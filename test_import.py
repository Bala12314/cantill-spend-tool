import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from spendkit.run import norm, stable

def test_norm():
    assert norm('ABC Ltd.') == 'ABC LTD'

def test_stable():
    assert stable('SG','ABC Ltd.') == stable('SG','abc ltd')
