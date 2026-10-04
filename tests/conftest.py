"""pytest 설정. src/ 안의 모듈들은 flat import(`from llm_client import ...`)를
전제로 작성되어 있어서(스크립트로 직접 실행될 때와 동일하게), 테스트에서도
src/를 sys.path에 추가해 같은 방식으로 import되게 한다. 소스 코드 구조는 건드리지 않는다.
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
