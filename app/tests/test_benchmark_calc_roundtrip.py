"""Regression checks for benchmark-discovered SQL expression/selection loss."""
import copy
import unittest
from app.tools.component_axes import _calc_field_add, _calc_field_update
from app.tools.component_crud import _update_component, _get_component_data


class Client:
    def __init__(self):
        self.report = {"ID": 64, "globalFilters": {"Заказчик": {"selected": ["Заказчик Б"], "enabled": True}},
            "grid": {"components": {"0": {"type": "HsTotalsPanelV2", "config": {"title": "Ratio", "chartType": "totalsPanelV2",
                "axes": [{"type": "filters", "fields": [{"name": "customer_name", "alias": "Заказчик", "global": True}]},
                         {"type": "values", "fields": [{"name": "plan_amount", "datasetId": 104, "agg": "sum", "id": "plan", "type": "number"}]}]}}}}}
        self.query = None

    async def api_call(self, entity, action, object_id=None, data=None):
        if entity == "reports" and action == "get":
            return {"status": 200, "data": [copy.deepcopy(self.report)]}
        if entity == "reports" and action == "update":
            self.report = copy.deepcopy(data[0])
            return {"status": 200}
        if entity == "datasets":
            return {"status": 200, "data": [{"fields": []}]}
        if entity == "recordsets":
            self.query = data[0]
            return {"status": 200, "data": [{"ratio": 0.7}]}
        raise AssertionError((entity, action))


class CalcRoundtripTests(unittest.IsolatedAsyncioTestCase):
    async def test_formula_survives_create_select_update_and_query(self):
        client = Client()
        formula = "SUM(completed_amount)/NULLIF(SUM(plan_amount),0)"
        created = await _calc_field_add(client, 64, 0, formula)
        field_name = created["field_name"]
        values = client.report["grid"]["components"]["0"]["config"]["axes"][1]["fields"]
        self.assertEqual(values[-1]["datasetId"], 104)
        self.assertEqual(values[-1]["calc"], formula)
        self.assertTrue(values[-1]["draft"])
        await _update_component(client, 64, 0, value_field=field_name)
        selected = client.report["grid"]["components"]["0"]["config"]["axes"][1]["fields"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["type"], "calculated")
        self.assertEqual(selected[0]["calc"], formula)
        await _get_component_data(client, 64, 0)
        self.assertEqual(client.query["select"][0]["calc"], formula)
        self.assertEqual(client.query["where"][0]["values"], ["Заказчик Б"])
        await _calc_field_update(client, 64, 0, field_name, calc_expression="100 * (" + formula + ")")
        self.assertTrue(client.report["grid"]["components"]["0"]["config"]["axes"][1]["fields"][0]["calc"].startswith("100 *"))

    async def test_stacked_series_are_grouped_in_data_readback(self):
        client = Client()
        client.report["grid"]["components"]["0"]["config"]["axes"] += [{"type": "series", "fields": [{"name": "payment_status", "datasetId": 104}]}]
        await _get_component_data(client, 64, 0)
        self.assertIn("payment_status", [g["name"] for g in client.query["group"]])


if __name__ == "__main__":
    unittest.main()
