from . import (
    username, email, domain, ip, phone, breach,
    image, crypto, social,
    ai_chat, ai_analyst, ai_pivot, ai_report, ai_auto,
    ai_correlate, ai_persona, ai_threat, ai_graph,
    ai_translate, ai_sockpuppet, ai_rag, ai_vision, ai_query,
)

OSINT_MODULES = [
    ("Username Hunter (40+ sites)",      username.run),
    ("Email Intelligence",                email.run),
    ("Domain & DNS Recon",                domain.run),
    ("IP Geolocation & Threat Intel",     ip.run),
    ("Phone Number Lookup",               phone.run),
    ("Data Breach Check",                 breach.run),
    ("Image Forensics (EXIF + Hash)",     image.run),
    ("Crypto Address Quick-Look",         crypto.run),
    ("Social Media Snapshot",             social.run),
]

AI_MODULES = [
    ("AI Chat (streaming + personas)",    ai_chat.run),
    ("AI Auto-Investigate (agentic)",     ai_auto.run),
    ("AI Natural-Language Query",         ai_query.run),
    ("AI Analyst (analyze findings)",     ai_analyst.run),
    ("AI Cross-Correlator",               ai_correlate.run),
    ("AI Persona Profiler",               ai_persona.run),
    ("AI Threat Scorer",                  ai_threat.run),
    ("AI Pivot Suggester",                ai_pivot.run),
    ("AI Link Graph (Mermaid)",           ai_graph.run),
    ("AI Report Writer (Markdown)",       ai_report.run),
    ("AI Translate",                      ai_translate.run),
    ("AI Sockpuppet / Stylometry",        ai_sockpuppet.run),
    ("AI RAG (Semantic Findings Search)", ai_rag.run),
    ("AI Vision (image understanding)",   ai_vision.run),
]

REGISTRY = OSINT_MODULES + AI_MODULES
