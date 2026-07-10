"""Declarative feature and alias registry for EDINET financials v1."""
from __future__ import annotations

FEATURE_SET = "edinet_financials_v1"
SCHEMA_VERSION = "1"
FEATURE_REGISTRY_VERSION = "1"
NORMALIZATION_VERSION = "1"

STATUS_CALCULATION = "CALCULATION"
STATUS_UNKNOWN = "UNKNOWN"

CLASS_OWN = "own"
CLASS_PROXY = "proxy"
CLASS_UNKNOWN = "UNKNOWN"

UNIT_RATIO = "ratio"
UNIT_JPY = "JPY"
UNIT_NULL = None

ALIASES = {
    "revenue": ("revenue", "net_sales", "sales"),
    "operating_income": ("operating_income", "operating_profit"),
    "net_income": ("net_income", "profit_attributable_to_owners_of_parent"),
    "equity": ("net_assets", "equity", "total_equity"),
    "total_assets": ("total_assets", "assets"),
    "operating_cash_flow": ("operating_cash_flow", "cash_flows_from_operating_activities", "cf_operating"),
    "capex": ("capital_expenditure", "purchase_of_property_plant_and_equipment", "capex"),
    "cash": ("cash_and_deposits", "cash_and_cash_equivalents", "cash"),
    "interest_bearing_debt": ("interest_bearing_debt", "borrowings", "bonds_payable"),
}

DEBT_COMPONENT_ALIASES = ("ibd_current", "ibd_noncurrent")

FEATURES = {
    "revenue_growth_yoy": {
        "classification": CLASS_OWN,
        "unit": UNIT_RATIO,
        "formula_id": "revenue_growth_yoy_v1",
    },
    "operating_margin": {
        "classification": CLASS_OWN,
        "unit": UNIT_RATIO,
        "formula_id": "operating_margin_v1",
    },
    "net_margin": {
        "classification": CLASS_OWN,
        "unit": UNIT_RATIO,
        "formula_id": "net_margin_v1",
    },
    "roe_proxy": {
        "classification": CLASS_PROXY,
        "unit": UNIT_RATIO,
        "formula_id": "roe_proxy_v1",
    },
    "roic_proxy": {
        "classification": CLASS_UNKNOWN,
        "unit": UNIT_NULL,
        "formula_id": "roic_proxy_unknown_v1",
    },
    "fcf_proxy": {
        "classification": CLASS_PROXY,
        "unit": UNIT_JPY,
        "formula_id": "fcf_proxy_v1",
    },
    "net_cash": {
        "classification": CLASS_OWN,
        "unit": UNIT_JPY,
        "formula_id": "net_cash_v1",
    },
    "equity_ratio": {
        "classification": CLASS_OWN,
        "unit": UNIT_RATIO,
        "formula_id": "equity_ratio_v1",
    },
    "valuation_status": {
        "classification": CLASS_UNKNOWN,
        "unit": UNIT_NULL,
        "formula_id": "valuation_status_unknown_v1",
    },
}


def registry_fingerprint_payload() -> dict:
    """Return the config_hash input payload owned by the feature layer."""
    return {
        "feature_set": FEATURE_SET,
        "schema_version": SCHEMA_VERSION,
        "feature_registry_version": FEATURE_REGISTRY_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "features": FEATURES,
        "aliases": ALIASES,
        "component_aliases": {
            "interest_bearing_debt": DEBT_COMPONENT_ALIASES,
        },
        "feature_assumptions": {
            "roic_proxy": "UNKNOWN_FIXED_PHASE_C_MINIMAL",
            "valuation_status": "UNKNOWN_FIXED_NO_PRICE_OR_MARKET_CAP_DATASET",
            "ratio_scale": "decimal_ratio",
        },
    }
