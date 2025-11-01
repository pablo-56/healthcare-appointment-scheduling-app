from app.tasks.eligibility import BILLING_ADAPTER_URL
import os

def test_adapter_url_default():
    assert BILLING_ADAPTER_URL.endswith(":9200")

def test_contract_shape():
    # Not calling HTTP – just shape expectations
    sample = {
        "eligible": True,
        "plan": "PPO-GOLD",
        "copay_cents": 2000,
        "raw_json": {"x12": {"response": {"271": {}}}},
    }
    assert isinstance(sample["eligible"], bool)
    assert isinstance(sample["plan"], str)
    assert isinstance(sample["copay_cents"], int)
    assert "raw_json" in sample
