import re
import unicodedata


def slugify(text: str) -> str:
    """Chuẩn hoá tên khái niệm thành id ổn định, dùng chung giữa roadmap node_id
    và graph_edges (source/target) để frontend map được cạnh nối vào đúng node
    khi vẽ sơ đồ (implementation_plan.md mục 4, tính năng roadmap dạng đồ thị)."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "concept"
