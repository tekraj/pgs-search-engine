from uuid import uuid4


DOMAINS: dict[str, dict] = {}


def create_domain(
    domain: str,
    enabled: bool = True,
    crawl_enabled: bool = True,
):

    if domain in DOMAINS:
        raise ValueError("Domain already exists")

    item = {
        "id": str(uuid4()),
        "domain": domain,
        "enabled": enabled,
        "crawl_enabled": crawl_enabled,
    }

    DOMAINS[domain] = item

    return item


def list_domains():

    return list(DOMAINS.values())


def update_domain(
    domain: str,
    enabled: bool | None = None,
    crawl_enabled: bool | None = None,
):

    item = DOMAINS.get(domain)

    if not item:
        raise ValueError("Domain not found")

    if enabled is not None:
        item["enabled"] = enabled

    if crawl_enabled is not None:
        item["crawl_enabled"] = crawl_enabled

    return item


def delete_domain(domain: str):

    if domain not in DOMAINS:
        raise ValueError("Domain not found")

    return DOMAINS.pop(domain)