import copy
import unittest
from app.tools.component_filters import _reset_global_filters


class Client:
    def __init__(self, local_selected):
        self.report = {"ID": 42, "globalFilters": {"Заказчик": {"selected": ["Заказчик Б"], "enabled": True, "filterMode": "by value"}},
            "grid": {"components": {"0": {"type": "HsFilterControlPanel", "config": {"selectedValue": local_selected, "filterApplied": bool(local_selected)}}}}}
        self.writes = 0

    async def api_call(self, entity, action, object_id=None, data=None):
        if action == "get":
            return {"status": 200, "data": [copy.deepcopy(self.report)]}
        if action == "update":
            self.report = copy.deepcopy(data[0])
            self.writes += 1
            return {"status": 200}
        raise AssertionError(action)


class ResetTests(unittest.IsolatedAsyncioTestCase):
    async def test_reset_clears_both_frontend_and_global_state(self):
        client = Client(["Заказчик Б"])
        result = await _reset_global_filters(client, 42)
        self.assertTrue(result["success"])
        self.assertEqual(client.report["globalFilters"]["Заказчик"]["selected"], [])
        self.assertEqual(client.report["grid"]["components"]["0"]["config"]["selectedValue"], [])

    async def test_global_selection_resets_even_if_panel_already_empty(self):
        client = Client([])
        await _reset_global_filters(client, 42)
        self.assertEqual(client.report["globalFilters"]["Заказчик"]["selected"], [])
        self.assertEqual(client.writes, 1)


if __name__ == "__main__":
    unittest.main()
