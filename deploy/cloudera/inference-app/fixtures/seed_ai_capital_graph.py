"""Build the CAI demo graph from publicly documented AI capital and supply relationships."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from semantica.context import ContextGraph


def _refs(*urls: str) -> str:
    return " | ".join(urls)


def _node_body(text: str, *sources: str) -> str:
    if not sources:
        return text
    return f"{text} Sources: {_refs(*sources)}"


def _edge_content(text: str, *sources: str) -> str:
    return _node_body(text, *sources)


def _provenance_fields(*source_urls: str) -> dict[str, str]:
    """Explorer UI reads source / source_url on node and edge properties."""
    if not source_urls:
        return {}
    return {"source_url": source_urls[0], "source": _refs(*source_urls)}


def _split_content_and_sources(content: str) -> tuple[str, tuple[str, ...]]:
    if " Sources: " not in content:
        return content, ()
    body, _, refs = content.partition(" Sources: ")
    urls = tuple(u.strip() for u in refs.split("|") if u.strip())
    return body.strip(), urls


# node_id -> (type, description with embedded sources)
NODES: dict[str, tuple[str, str]] = {
    "demo_disclaimer": (
        "metadata",
        _node_body(
            "Semantica Explorer demo graph for Cloudera AI. Nodes and edges summarize "
            "public filings, company press releases, and major news reports. Amounts use "
            "the units stated in each source (USD unless noted). Not investment advice.",
            "https://openai.com/index/announcing-the-stargate-project/",
            "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-ex99_2.htm",
        ),
    ),
    "openai": (
        "company",
        _node_body(
            "OpenAI — developer of GPT and related frontier models; Microsoft minority "
            "shareholder; Stargate operational partner.",
            "https://openai.com/index/announcing-the-stargate-project/",
            "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-ex99_2.htm",
        ),
    ),
    "microsoft": (
        "company",
        _node_body(
            "Microsoft — Azure cloud; ~27% OpenAI PBC stake (as-converted, Oct 2025 recap); "
            "Mistral and Inflection partnerships.",
            "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-ex99_2.htm",
            "https://azure.microsoft.com/en-us/blog/microsoft-and-mistral-ai-announce-new-partnership-to-accelerate-ai-innovation-and-introduce-mistral-large-first-on-azure/",
        ),
    ),
    "anthropic": (
        "company",
        _node_body(
            "Anthropic — Claude models; AWS primary training partner; Google Cloud TPU customer.",
            "https://www.aboutamazon.com/news/company-news/amazon-anthropic-ai-investment",
            "https://www.googlecloudpresscorner.com/2023-11-08-Google-Announces-Expansion-of-AI-Partnership-with-Anthropic",
        ),
    ),
    "amazon": (
        "company",
        _node_body(
            "Amazon — parent of AWS; completed $4B Anthropic investment (Mar 2024).",
            "https://www.aboutamazon.com/news/company-news/amazon-anthropic-ai-investment",
            "https://press.aboutamazon.com/2023/9/amazon-and-anthropic-announce-strategic-collaboration-to-advance-generative-ai",
        ),
    ),
    "google": (
        "company",
        _node_body(
            "Alphabet / Google — Google Cloud; up to $2B Anthropic commitment (Oct 2023 reporting).",
            "https://www.reuters.com/technology/google-agrees-invest-up-2-bln-openai-rival-anthropic-wsj-2023-10-27/",
            "https://www.googlecloudpresscorner.com/2023-11-08-Google-Announces-Expansion-of-AI-Partnership-with-Anthropic",
        ),
    ),
    "nvidia": (
        "company",
        _node_body(
            "NVIDIA — AI accelerators and software; OpenAI collaborator since 2016; Stargate technology partner.",
            "https://openai.com/index/announcing-the-stargate-project/",
            "https://investor.nvidia.com/",
        ),
    ),
    "oracle": (
        "company",
        _node_body(
            "Oracle — cloud infrastructure; Stargate initial equity funder and technology partner.",
            "https://openai.com/index/announcing-the-stargate-project/",
            "https://group.softbank/en/news/press/20250122",
        ),
    ),
    "softbank": (
        "investor",
        _node_body(
            "SoftBank Group — Stargate lead financial partner; Masa Son chairman; Arm owner.",
            "https://group.softbank/en/news/press/20250122",
            "https://www.govinfo.gov/content/pkg/DCPD-202500157/html/DCPD-202500157.htm",
        ),
    ),
    "mgx": (
        "investor",
        _node_body(
            "MGX — Abu Dhabi investment vehicle; listed as initial Stargate equity funder.",
            "https://openai.com/index/announcing-the-stargate-project/",
        ),
    ),
    "mistral": (
        "company",
        _node_body(
            "Mistral AI — French frontier lab; Azure distribution and Microsoft €15M investment (Feb 2024).",
            "https://azure.microsoft.com/en-us/blog/microsoft-and-mistral-ai-announce-new-partnership-to-accelerate-ai-innovation-and-introduce-mistral-large-first-on-azure/",
            "https://techcrunch.com/2024/02/27/microsoft-made-a-16-million-investment-in-mistral-ai/",
        ),
    ),
    "inflection_ai": (
        "company",
        _node_body(
            "Inflection AI — Pi assistant developer; 2024 licensing deal with Microsoft after staff hire.",
            "https://www.reuters.com/technology/microsoft-agreed-pay-inflection-650-mln-while-hiring-its-staff-information-2024-03-21/",
            "https://assets.publishing.service.gov.uk/media/6719ff5f549f63039436b3c8/__Full_text_decision__.pdf",
        ),
    ),
    "character_ai": (
        "company",
        _node_body(
            "Character.AI — consumer chatbots; Aug 2024 non-exclusive Google license; "
            "Alphabet recorded $2.7B cash payment in Q3 2024 filings.",
            "https://www.reuters.com/technology/artificial-intelligence/google-hires-characterai-cofounders-licenses-its-models-information-reports-2024-08-02/",
            "https://www.sec.gov/Archives/edgar/data/1652044/000165204424000118/R16.htm",
        ),
    ),
    "amd": (
        "company",
        _node_body(
            "AMD — MI300 accelerators offered on Azure alongside NVIDIA options.",
            "https://azure.microsoft.com/en-us/blog/introducing-the-new-ai-accelerator-optimized-vms-with-amd-mi300x/",
        ),
    ),
    "intel": (
        "company",
        _node_body(
            "Intel — Gaudi AI accelerators available on Azure and AWS.",
            "https://www.intel.com/content/www/us/en/newsroom/news/intel-gaudi-3-ai-accelerator.html",
        ),
    ),
    "apple": (
        "company",
        _node_body(
            "Apple — Apple Intelligence platform; uses Google Cloud for some AI features per reporting.",
            "https://www.reuters.com/technology/apple-holds-talks-with-google-bring-gemini-ai-iphone-2024-03-18/",
        ),
    ),
    "coreweave": (
        "company",
        _node_body(
            "CoreWeave — GPU-focused cloud; NVIDIA-backed neocloud; OpenAI capacity supplier (reporting).",
            "https://www.nvidia.com/en-us/geforce/news/coreweave-secures-2-3b-debt-financing-for-ai-infrastructure/",
            "https://www.reuters.com/technology/artificial-intelligence/openai-uses-nvidia-rival-chips-amid-chip-shortage-2024-03-20/",
        ),
    ),
    "meta": (
        "company",
        _node_body(
            "Meta — Llama models; disclosed multi-billion-dollar AI infrastructure capex.",
            "https://investor.atmeta.com/investor-news/press-release-details/2024/Meta-Reports-Fourth-Quarter-and-Full-Year-2023-Results/default.aspx",
        ),
    ),
    "xai": (
        "company",
        _node_body(
            "xAI — Grok developer; raised billions from private investors (2024–2025 reporting).",
            "https://www.reuters.com/technology/artificial-intelligence/musks-xai-raises-6-billion-funding-valuation-24-billion-2024-05-26/",
        ),
    ),
    "cohere": (
        "company",
        _node_body(
            "Cohere — enterprise LLMs; Oracle and NVIDIA among strategic investors (company disclosures).",
            "https://cohere.com/blog/series-d",
            "https://www.oracle.com/news/announcement/oracle-invests-in-cohere-2023-06-08/",
        ),
    ),
    "databricks": (
        "company",
        _node_body(
            "Databricks — data/AI platform; mutual strategic investment with NVIDIA (2023).",
            "https://www.nvidia.com/en-us/about-nvidia/press-releases/2023/nvidia-databricks-strategic-partnership/",
        ),
    ),
    "arm": (
        "company",
        _node_body(
            "Arm Holdings — CPU IP; SoftBank-majority; Stargate initial technology partner.",
            "https://openai.com/index/announcing-the-stargate-project/",
        ),
    ),
    "tsmc": (
        "company",
        _node_body(
            "TSMC — foundry manufacturing NVIDIA and other AI accelerators.",
            "https://www.tsmc.com/static/abouttsmcaz/nasdaq_ir/annual-reports/2023/english/index.html",
        ),
    ),
    "stargate_project": (
        "initiative",
        _node_body(
            "Stargate Project — JV announced Jan 21, 2025; up to $500B U.S. AI infrastructure "
            "intent over four years; $100B immediate deployment stated by partners.",
            "https://openai.com/index/announcing-the-stargate-project/",
            "https://www.govinfo.gov/content/pkg/DCPD-202500157/html/DCPD-202500157.htm",
        ),
    ),
    "azure_openai_service": (
        "product",
        _node_body(
            "Azure OpenAI Service — Microsoft distribution of OpenAI models to enterprise.",
            "https://www.sec.gov/Archives/edgar/data/789019/000095017023035122/msft-20230630.htm",
        ),
    ),
    "amazon_bedrock": (
        "product",
        _node_body(
            "Amazon Bedrock — AWS managed API for foundation models including Anthropic Claude.",
            "https://press.aboutamazon.com/2023/9/amazon-and-anthropic-announce-strategic-collaboration-to-advance-generative-ai",
        ),
    ),
    "founders_fund": (
        "investor",
        _node_body(
            "Founders Fund — reported participant in xAI funding rounds.",
            "https://www.reuters.com/technology/artificial-intelligence/musks-xai-raises-6-billion-funding-valuation-24-billion-2024-05-26/",
        ),
    ),
    "sequoia_capital": (
        "investor",
        _node_body(
            "Sequoia Capital — early Anthropic investor (company history).",
            "https://www.anthropic.com/news/anthropic-series-c",
        ),
    ),
    "nvidia_nventures": (
        "investor",
        _node_body(
            "NVentures — NVIDIA venture arm; portfolio includes CoreWeave, Cohere, others.",
            "https://www.nvidia.com/en-us/about-nvidia/ventures/",
        ),
    ),
}


def _e(
    source: str,
    target: str,
    rel: str,
    summary: str,
    *source_urls: str,
    **fields: Any,
) -> tuple[str, str, str, dict[str, Any]]:
    props: dict[str, Any] = {
        "content": _edge_content(summary, *source_urls),
        "source_urls": _refs(*source_urls),
        **_provenance_fields(*source_urls),
    }
    props.update({k: v for k, v in fields.items() if v is not None})
    return (source, target, rel, props)


# Grounded edges — amounts only when explicitly stated in cited sources
EDGES: list[tuple[str, str, str, dict[str, Any]]] = [
    _e(
        "microsoft",
        "openai",
        "funding_commitment",
        "Microsoft total OpenAI funding commitments $13B ($11.8B funded as of Mar 31, 2026 per filings); "
        "~27% OpenAI Group PBC stake after Oct 2025 recap.",
        "https://www.sec.gov/Archives/edgar/data/789019/000119312525256321/R26.htm",
        "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-ex99_2.htm",
        amount_usd_b=13,
        instrument="equity_method_investment",
        status="active",
    ),
    _e(
        "openai",
        "microsoft",
        "azure_services_contract",
        "OpenAI contracted to purchase incremental $250B of Azure services (Oct 28, 2025 agreement).",
        "https://www.sec.gov/Archives/edgar/data/789019/000119312525256321/R26.htm",
        "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-ex99_2.htm",
        amount_usd_b=250,
        instrument="cloud_services_purchase",
        status="announced",
    ),
    _e(
        "microsoft",
        "azure_openai_service",
        "operates",
        "Azure OpenAI Service offers OpenAI models to enterprise customers.",
        "https://www.sec.gov/Archives/edgar/data/789019/000095017023035122/msft-20230630.htm",
        instrument="product",
        status="active",
    ),
    _e(
        "amazon",
        "anthropic",
        "equity_investment",
        "Amazon completed $4B total investment in Anthropic ($1.25B Sep 2023 + $2.75B Mar 2024).",
        "https://www.aboutamazon.com/news/company-news/amazon-anthropic-ai-investment",
        "https://apnews.com/article/amazon-anthropic-investment-ai-big-tech-f5108beaa33455f331010489e03586d4",
        amount_usd_b=4,
        instrument="equity_minority",
        status="completed",
    ),
    _e(
        "anthropic",
        "amazon",
        "primary_cloud_and_training",
        "Anthropic names AWS primary cloud provider and primary training partner; uses Trainium/Inferentia.",
        "https://www.aboutamazon.com/news/aws/amazon-invests-additional-4-billion-anthropic-ai/",
        "https://press.aboutamazon.com/2023/9/amazon-and-anthropic-announce-strategic-collaboration-to-advance-generative-ai",
        instrument="cloud_partnership",
        status="active",
    ),
    _e(
        "anthropic",
        "amazon_bedrock",
        "model_distribution",
        "Claude models available to AWS customers via Amazon Bedrock.",
        "https://press.aboutamazon.com/2023/9/amazon-and-anthropic-announce-strategic-collaboration-to-advance-generative-ai",
        instrument="distribution",
        status="active",
    ),
    _e(
        "google",
        "anthropic",
        "convertible_note_investment",
        "Google agreed to invest up to $2B ($500M upfront + $1.5B over time), structured as convertible note per Anthropic spokesperson.",
        "https://www.reuters.com/technology/google-agrees-invest-up-2-bln-openai-rival-anthropic-wsj-2023-10-27/",
        amount_usd_b=2,
        instrument="convertible_note",
        status="announced",
    ),
    _e(
        "anthropic",
        "google",
        "cloud_compute",
        "Anthropic expanded Google Cloud partnership; uses Cloud TPU v5e for inference workloads.",
        "https://www.googlecloudpresscorner.com/2023-11-08-Google-Announces-Expansion-of-AI-Partnership-with-Anthropic",
        instrument="cloud_partnership",
        status="active",
    ),
    _e(
        "microsoft",
        "mistral",
        "investment_and_partnership",
        "Microsoft €15M investment (converts to equity in next round) plus multi-year Azure partnership; Mistral Large on Azure.",
        "https://azure.microsoft.com/en-us/blog/microsoft-and-mistral-ai-announce-new-partnership-to-accelerate-ai-innovation-and-introduce-mistral-large-first-on-azure/",
        "https://techcrunch.com/2024/02/27/microsoft-made-a-16-million-investment-in-mistral-ai/",
        amount_usd_m=16,
        instrument="equity_commitment",
        status="active",
    ),
    _e(
        "mistral",
        "microsoft",
        "azure_hosting",
        "Mistral models hosted in Azure AI model catalog for enterprise customers.",
        "https://azure.microsoft.com/en-us/blog/microsoft-and-mistral-ai-announce-new-partnership-to-accelerate-ai-innovation-and-introduce-mistral-large-first-on-azure/",
        instrument="distribution",
        status="active",
    ),
    _e(
        "microsoft",
        "inflection_ai",
        "licensing_and_hiring",
        "Microsoft agreed to pay ~$650M ($620M non-exclusive IP license + ~$30M waiver) while hiring Inflection leadership/staff.",
        "https://www.reuters.com/technology/microsoft-agreed-pay-inflection-650-mln-while-hiring-its-staff-information-2024-03-21/",
        "https://assets.publishing.service.gov.uk/media/6719ff5f549f63039436b3c8/__Full_text_decision__.pdf",
        amount_usd_m=650,
        instrument="license_and_settlement",
        status="closed",
    ),
    _e(
        "google",
        "character_ai",
        "licensing_agreement",
        "Non-exclusive LLM license; Alphabet paid $2.7B cash and canceled convertible instruments; hired co-founders.",
        "https://www.reuters.com/technology/artificial-intelligence/google-hires-characterai-cofounders-licenses-its-models-information-reports-2024-08-02/",
        "https://www.sec.gov/Archives/edgar/data/1652044/000165204424000118/R16.htm",
        amount_usd_b=2.7,
        instrument="license",
        status="closed",
    ),
    _e(
        "microsoft",
        "amd",
        "cloud_accelerator_supply",
        "Azure offers AI-optimized VMs with AMD MI300X accelerators.",
        "https://azure.microsoft.com/en-us/blog/introducing-the-new-ai-accelerator-optimized-vms-with-amd-mi300x/",
        instrument="cloud_SKU",
        status="active",
    ),
    _e(
        "microsoft",
        "intel",
        "cloud_accelerator_supply",
        "Azure hosts Intel Gaudi 3 accelerator instances for AI workloads.",
        "https://www.intel.com/content/www/us/en/newsroom/news/intel-gaudi-3-ai-accelerator.html",
        instrument="cloud_SKU",
        status="active",
    ),
    _e(
        "apple",
        "google",
        "ai_feature_partnership_talks",
        "Reuters reported Apple held talks to license Google Gemini for iPhone AI features (Mar 2024).",
        "https://www.reuters.com/technology/apple-holds-talks-with-google-bring-gemini-ai-iphone-2024-03-18/",
        instrument="licensing_negotiation",
        status="reported",
    ),
    _e(
        "softbank",
        "arm",
        "majority_shareholder",
        "SoftBank remains controlling shareholder of Arm after 2023 IPO.",
        "https://group.softbank/en/ir/financials/annual_reports",
        instrument="equity_control",
        status="active",
    ),
    _e(
        "nvidia",
        "arm",
        "terminated_acquisition",
        "NVIDIA-Arm acquisition terminated Feb 2022 after regulatory opposition.",
        "https://nvidianews.nvidia.com/news/nvidia-and-softbank-group-announce-termination-of-nvidias-acquisition-of-arm-limited",
        instrument="M&A",
        status="terminated",
    ),
    _e(
        "softbank",
        "stargate_project",
        "lead_financial_partner",
        "SoftBank lead financial partner for Stargate; Masayoshi Son chairman.",
        "https://group.softbank/en/news/press/20250122",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="project_equity",
        status="announced",
    ),
    _e(
        "openai",
        "stargate_project",
        "operational_partner",
        "OpenAI operational responsibility for Stargate infrastructure buildout.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="project_operations",
        status="announced",
    ),
    _e(
        "oracle",
        "stargate_project",
        "equity_and_technology",
        "Oracle initial equity funder and technology partner for Stargate data centers.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="project_equity",
        status="announced",
    ),
    _e(
        "mgx",
        "stargate_project",
        "equity_funding",
        "MGX listed among initial Stargate equity funders.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="project_equity",
        status="announced",
    ),
    _e(
        "nvidia",
        "stargate_project",
        "technology_partner",
        "NVIDIA named key initial technology partner for Stargate compute buildout.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="technology_alliance",
        status="announced",
    ),
    _e(
        "microsoft",
        "stargate_project",
        "technology_partner",
        "Microsoft named key initial technology partner for Stargate.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="technology_alliance",
        status="announced",
    ),
    _e(
        "arm",
        "stargate_project",
        "technology_partner",
        "Arm named key initial technology partner for Stargate.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="technology_alliance",
        status="announced",
    ),
    _e(
        "nvidia",
        "openai",
        "technology_collaboration",
        "OpenAI cites NVIDIA collaboration dating to 2016; Stargate joint operations for compute systems.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="supply_and_R&D",
        status="active",
    ),
    _e(
        "openai",
        "coreweave",
        "gpu_capacity",
        "OpenAI used CoreWeave for additional GPU capacity amid supply constraints (Reuters reporting).",
        "https://www.reuters.com/technology/artificial-intelligence/openai-uses-nvidia-rival-chips-amid-chip-shortage-2024-03-20/",
        instrument="cloud_capacity",
        status="reported",
    ),
    _e(
        "coreweave",
        "nvidia",
        "debt_financing_for_gpus",
        "CoreWeave secured $2.3B debt financing backed by NVIDIA H100 contracts (NVIDIA press release).",
        "https://www.nvidia.com/en-us/geforce/news/coreweave-secures-2-3b-debt-financing-for-ai-infrastructure/",
        amount_usd_b=2.3,
        instrument="secured_debt",
        status="announced",
    ),
    _e(
        "nvidia_nventures",
        "coreweave",
        "venture_investment",
        "NVentures portfolio company; NVIDIA ecosystem neocloud partner.",
        "https://www.nvidia.com/en-us/about-nvidia/ventures/",
        instrument="equity",
        status="active",
    ),
    _e(
        "founders_fund",
        "xai",
        "venture_investment",
        "xAI raised $6B series B at ~$24B valuation; Founders Fund among investors cited by Reuters.",
        "https://www.reuters.com/technology/artificial-intelligence/musks-xai-raises-6-billion-funding-valuation-24-billion-2024-05-26/",
        amount_usd_b=6,
        instrument="equity",
        status="reported",
    ),
    _e(
        "xai",
        "nvidia",
        "accelerator_supply",
        "xAI Colossus and expansion clusters rely on large NVIDIA GPU deployments (company and industry reporting).",
        "https://www.reuters.com/technology/artificial-intelligence/musks-xai-raises-6-billion-funding-valuation-24-billion-2024-05-26/",
        instrument="hardware_supply",
        status="active",
    ),
    _e(
        "meta",
        "nvidia",
        "infrastructure_capex",
        "Meta guided tens of billions in 2024 capex driven largely by AI infrastructure including NVIDIA GPUs.",
        "https://investor.atmeta.com/investor-news/press-release-details/2024/Meta-Reports-Fourth-Quarter-and-Full-Year-2023-Results/default.aspx",
        instrument="capex",
        status="disclosed",
    ),
    _e(
        "oracle",
        "cohere",
        "strategic_investment",
        "Oracle invested in Cohere and partners on OCI deployment (Oracle announcement Jun 2023).",
        "https://www.oracle.com/news/announcement/oracle-invests-in-cohere-2023-06-08/",
        instrument="equity",
        status="announced",
    ),
    _e(
        "nvidia",
        "databricks",
        "strategic_partnership",
        "NVIDIA and Databricks announced strategic partnership and mutual investment (2023).",
        "https://www.nvidia.com/en-us/about-nvidia/press-releases/2023/nvidia-databricks-strategic-partnership/",
        instrument="alliance",
        status="active",
    ),
    _e(
        "sequoia_capital",
        "anthropic",
        "venture_investment",
        "Sequoia participated in Anthropic Series C (company announcement).",
        "https://www.anthropic.com/news/anthropic-series-c",
        instrument="equity",
        status="historical",
    ),
    _e(
        "demo_disclaimer",
        "openai",
        "documents",
        "Demo edge — verify live terms via cited primary sources before business use.",
        "https://openai.com/index/announcing-the-stargate-project/",
        instrument="metadata",
        status="demo",
    ),
]


def populate_ai_capital_graph(graph: ContextGraph) -> None:
    for node_id, (node_type, content) in NODES.items():
        _, urls = _split_content_and_sources(content)
        graph.add_node(
            node_id,
            node_type,
            content=content,
            **_provenance_fields(*urls),
        )

    for source, target, edge_type, props in EDGES:
        graph.add_edge(source, target, edge_type, **props)


def build_sources_manifest(graph_path: Path) -> dict[str, Any]:
    """Bibliography for default demo resources (served by launch_app /api/demo/resources)."""
    references: dict[str, dict[str, str]] = {}
    for _node_id, (_ntype, content) in NODES.items():
        _, urls = _split_content_and_sources(content)
        for url in urls:
            references.setdefault(url, {"url": url, "kind": "node_citation"})
    for _src, _tgt, _rel, props in EDGES:
        raw = str(props.get("source_urls") or props.get("source") or "")
        for url in (u.strip() for u in raw.split("|")):
            if url.startswith("http"):
                references.setdefault(url, {"url": url, "kind": "edge_citation"})
    return {
        "default_graph": graph_path.name,
        "description": (
            "Grounded AI industry capital/supply demo for Cloudera AI Knowledge Explorer. "
            "Node/edge inspector shows source and source_url; full text includes inline citations."
        ),
        "regenerate": "python deploy/cloudera/inference-app/fixtures/seed_ai_capital_graph.py",
        "references": sorted(references.values(), key=lambda item: item["url"]),
    }


def write_sources_manifest(fixtures_dir: Path, graph_path: Path) -> Path:
    import json

    manifest = build_sources_manifest(graph_path)
    out = fixtures_dir / "demo_resources.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out


def write_ai_capital_graph(path: Path) -> None:
    graph = ContextGraph()
    populate_ai_capital_graph(graph)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.save_to_file(str(path))
    write_sources_manifest(path.parent, path)


if __name__ == "__main__":
    default = Path(__file__).resolve().parent / "ai_capital_graph.json"
    write_ai_capital_graph(default)
    verify = ContextGraph()
    verify.load_from_file(str(default))
    print(f"Wrote {default} — nodes={len(verify.nodes)} edges={len(verify.edges)}")
