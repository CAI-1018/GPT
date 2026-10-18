#!/usr/bin/env python3
"""A dependency-free JSON memory store with a disposable SQLite index."""
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent
FIELDS = ('id', 'category', 'key', 'value', 'observed_on', 'source', 'status',
          'confidence', 'sensitivity', 'review_on', 'supersedes')


def validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('schema_version 必须为 1')
    date.fromisoformat(data['snapshot_date'])
    if not isinstance(data.get('timezone'), str):
        raise ValueError('缺少 timezone')
    if not isinstance(data.get('scope'), str):
        raise ValueError('缺少 scope')
    if not isinstance(data.get('memories'), list):
        raise ValueError('memories 必须为数组')
    seen = set()
    for row in data['memories']:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError('记录字段与 schema 不一致')
        for field in ('id', 'category', 'key', 'value'):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f'{field} 必须为非空字符串')
        if row['id'] in seen:
            raise ValueError(f'重复 ID: {row["id"]}')
        seen.add(row['id'])
        for field in ('observed_on', 'review_on'):
            if row[field] is not None:
                date.fromisoformat(row[field])
        if not isinstance(row['source'], dict) or not row['source'].get('kind') or not row['source'].get('note'):
            raise ValueError('source 必须含 kind 与 note')
        for field, choices in (
            ('status', ('active', 'historical', 'needs_confirmation')),
            ('confidence', ('reported', 'inferred')),
            ('sensitivity', ('personal', 'sensitive')),
        ):
            if row[field] not in choices:
                raise ValueError(f'无效 {field}')
    parents = {}
    for row in data['memories']:
        parent = row['supersedes']
        if parent is not None:
            if not isinstance(parent, str) or parent not in seen or parent == row['id']:
                raise ValueError('supersedes 必须引用其他存在的 ID')
            parents[row['id']] = parent
    for item in parents:
        visited = set()
        while item in parents:
            if item in visited:
                raise ValueError('supersedes 存在循环')
            visited.add(item)
            item = parents[item]
    return data


def load(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8')))


def select(data, terms=(), category=None, include_all=False):
    return [row for row in data['memories']
            if (include_all or row['status'] == 'active')
            and (category is None or row['category'] == category)
            and all(term.casefold() in '\n'.join((row['key'], row['value'], row['category'])).casefold()
                    for term in terms)]


def build(data, db_path):
    validate(data)  # Validate the entire source before touching an existing index.
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        # execute individually: executescript would implicitly commit transactions.
        con.execute('BEGIN IMMEDIATE')
        for statement in (ROOT / 'schema.sql').read_text(encoding='utf-8').split(';'):
            if statement.strip():
                con.execute(statement)
        con.execute('DELETE FROM memories')
        con.execute('DELETE FROM metadata')
        con.executemany('INSERT INTO metadata VALUES (?, ?)',
                        [(k, json.dumps(v, ensure_ascii=False)) for k, v in data.items() if k != 'memories'])
        con.executemany('INSERT INTO memories VALUES (' + ','.join('?' for _ in FIELDS) + ')',
                        [tuple(json.dumps(r[f], ensure_ascii=False) if f == 'source' else r[f]
                               for f in FIELDS) for r in data['memories']])


def context(data, rows):
    try:
        today = datetime.now(ZoneInfo(data['timezone'])).date().isoformat()
    except ZoneInfoNotFoundError:
        # Windows may lack IANA tzdata; China has a stable UTC+8 offset.
        if data['timezone'] != 'Asia/Shanghai':
            raise ValueError('本机缺少该时区数据')
        from datetime import timedelta, timezone
        today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    lines = ['# 个人记忆交接', '', f'快照：{data["snapshot_date"]}；范围：{data["scope"]}。',
             '来源为会话摘要的条目未经原始聊天逐条核验。动态信息须结合日期使用。', '']
    for r in rows:
        stale = '；待复核（已到建议日期）' if r['review_on'] and r['review_on'] <= today else ''
        lines += [f'## {r["id"]} · {r["key"]}', '', r['value'], '',
                  f'- 分类：{r["category"]}；状态：{r["status"]}{stale}',
                  f'- 信息日期：{r["observed_on"] or "未明确"}；性质：{r["confidence"]}；敏感度：{r["sensitivity"]}',
                  f'- 来源：{r["source"]["kind"]} / {r["source"]["note"]}',
                  f'- 建议复核：{r["review_on"] or "按需"}；替代记录：{r["supersedes"] or "无"}', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('validate', 'build', 'search', 'context', 'stats'))
    parser.add_argument('terms', nargs='*')
    parser.add_argument('--source', type=Path, default=ROOT / 'private/memories.json')
    parser.add_argument('--db', type=Path, default=ROOT / 'private/memory.sqlite3')
    parser.add_argument('--category')
    parser.add_argument('--all', action='store_true', dest='include_all')
    args = parser.parse_args()
    try:
        data = load(args.source)
        rows = select(data, args.terms, args.category, args.include_all)
        if args.command == 'validate':
            print(f'校验通过：{len(data["memories"])} 条记录')
        elif args.command == 'build':
            if args.db.resolve() in (args.source.resolve(), (ROOT / 'schema.sql').resolve(), Path(__file__).resolve()):
                raise ValueError('数据库输出不得覆盖源文件或程序')
            build(data, args.db)
            print(f'索引已建立：{len(data["memories"])} 条记录')
        elif args.command == 'context':
            print(context(data, rows))
        elif args.command == 'stats':
            from collections import Counter
            print(json.dumps({'total': len(data['memories']),
                              'status': dict(Counter(r['status'] for r in data['memories'])),
                              'category': dict(Counter(r['category'] for r in data['memories']))}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
