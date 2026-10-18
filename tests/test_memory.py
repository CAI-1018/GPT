import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import memory


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.data = memory.load(memory.ROOT / 'examples/memories.json')

    def test_chinese_and_historical_filters(self):
        self.assertEqual(len(memory.select(self.data, ['考试'])), 1)
        self.assertEqual(memory.select(self.data, ["' OR 1=1 --"]), [])
        self.data['memories'][0]['status'] = 'historical'
        self.assertEqual(memory.select(self.data), [])
        self.assertEqual(len(memory.select(self.data, include_all=True)), 1)

    def test_duplicate_ids_are_rejected(self):
        self.data['memories'].append(copy.deepcopy(self.data['memories'][0]))
        with self.assertRaises(ValueError):
            memory.validate(self.data)

    def test_supersedes_missing_and_cycle(self):
        self.data['memories'][0]['supersedes'] = 'missing'
        with self.assertRaises(ValueError):
            memory.validate(self.data)
        other = copy.deepcopy(self.data['memories'][0])
        other['id'] = 'example-002'
        other['supersedes'] = 'example-001'
        self.data['memories'][0]['supersedes'] = 'example-002'
        self.data['memories'].append(other)
        with self.assertRaises(ValueError):
            memory.validate(self.data)

    def test_index_rebuild_and_invalid_source_preserves_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'test.sqlite3'
            memory.build(self.data, db)
            memory.build(self.data, db)
            self.data['memories'][0]['status'] = 'invalid'
            with self.assertRaises(ValueError):
                memory.build(self.data, db)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute('SELECT COUNT(*) FROM memories').fetchone()[0], 1)
                source = json.loads(con.execute('SELECT source FROM memories').fetchone()[0])
                self.assertEqual(source['kind'], 'fictional_example')

    def test_context_marks_review_due(self):
        self.data['memories'][0]['review_on'] = '2000-01-01'
        text = memory.context(self.data, self.data['memories'])
        self.assertIn('待复核', text)
        self.assertIn('虚构示例', text)


if __name__ == '__main__':
    unittest.main()
