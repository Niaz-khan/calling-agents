"""Idempotent seeding of default public website content.

Only fills rows that do not already exist, so later CMS edits are never
overwritten. Called by the ``seed_cms`` management command and by the initial
data migration.
"""

from .models import (
    DEFAULT_SECTIONS,
    FAQ,
    FeatureSection,
    FooterSection,
    LandingPage,
    NavigationItem,
    PricingPlan,
    SiteSettings,
    Testimonial,
    UseCase,
)


def _seed_list(model, items):
    if model.objects.exists():
        return
    model.objects.bulk_create([model(**item, order=i) for i, item in enumerate(items)])


DEFAULT_FEATURES = [
    {
        "title": "AI Phone Agent",
        "icon": "phone",
        "description": "Answer inbound calls naturally, understand customers, and take action.",
    },
    {
        "title": "Website Agent",
        "icon": "website",
        "description": "Add an AI assistant to any website with a simple embed snippet.",
    },
    {
        "title": "Appointment Booking",
        "icon": "calendar",
        "description": "Check availability and book appointments without human intervention.",
    },
    {
        "title": "Business Knowledge",
        "icon": "knowledge",
        "description": "Give your agent access to your services, FAQs, documents and business information.",
    },
    {
        "title": "Customer Memory",
        "icon": "customers",
        "description": "Remember previous conversations so returning customers don't have to repeat themselves.",
    },
    {
        "title": "Human Transfer",
        "icon": "transfer",
        "description": "Let AI handle the routine and seamlessly transfer important conversations to your team.",
    },
    {
        "title": "Call Analytics",
        "icon": "analytics",
        "description": "Understand conversations, outcomes, appointments, transfers and customer activity.",
    },
    {
        "title": "Outbound Calling",
        "icon": "outbound",
        "description": "Reach customers proactively when your business needs to.",
    },
]

DEFAULT_USE_CASES = [
    {
        "title": "Dental clinics",
        "icon": "health",
        "description": "Answer booking questions, confirm appointments and capture patient details.",
    },
    {
        "title": "Medical practices",
        "icon": "health",
        "description": "Route routine enquiries and schedule visits without a busy front desk.",
    },
    {
        "title": "Law firms",
        "icon": "briefcase",
        "description": "Qualify enquiries, collect intake details and hand off to an attorney.",
    },
    {
        "title": "Real estate",
        "icon": "home",
        "description": "Respond to listing questions and capture qualified buyer or seller leads.",
    },
    {
        "title": "Salons",
        "icon": "scissors",
        "description": "Book appointments and answer pricing and availability questions.",
    },
    {
        "title": "Home services",
        "icon": "wrench",
        "description": "Take service requests, answer FAQs and schedule visits — day or night.",
    },
    {
        "title": "Restaurants",
        "icon": "restaurant",
        "description": "Take reservations and answer hours, menu and location questions.",
    },
    {
        "title": "Automotive",
        "icon": "car",
        "description": "Book service visits and answer pricing, warranty and hours questions.",
    },
    {
        "title": "Professional services",
        "icon": "briefcase",
        "description": "Capture enquiries and book consultations without a receptionist.",
    },
    {
        "title": "Consulting",
        "icon": "briefcase",
        "description": "Capture enquiries, gather project details and book discovery calls.",
    },
    {
        "title": "Small business",
        "icon": "store",
        "description": "One agent that never misses a call, however small your team is.",
    },
]

DEFAULT_FAQS = [
    {
        "question": "What is an AI business agent?",
        "answer": "An AI business agent answers calls and website chats for your business — "
        "understand questions, book appointments, share your services and knowledge, "
        "and hand conversations humans when needed.",
    },
    {
        "question": "Can it answer phone calls?",
        "answer": "Yes. Once a phone number is connected and assigned to an agent, inbound "
        "calls are answered by the agent automatically and outbound calls can be "
        "placed from the dashboard.",
    },
    {
        "question": "Do I need a phone number to use the website agent?",
        "answer": "No. Website is the fastest way to start - add the chat agent to your site "
        "with a single line of code, no phone number required. You can add a "
        "business phone number whenever you're ready.",
    },
    {
        "question": "Can it work on my website?",
        "answer": "Yes. Create a website deployment, copy the snippet, and paste it before "
        "</body> on your site. The widget shows in the corner and opens a live chat "
        "with your agent.",
    },
    {
        "question": "Can it book appointments?",
        "answer": "Yes. With services and availability configured, the agent checks the "
        "calendar and books appointments through the backend so it never promises "
        "a slot that conflicts.",
    },
    {
        "question": "Can I give it my business knowledge?",
        "answer": "Yes. A knowledge base can be attached to each agent and populated with "
        "documents (PDFs and text). Search uses embeddings so the agent answers from "
        "your own information.",
    },
    {
        "question": "Can it transfer calls to employees?",
        "answer": "Yes. The agent can transfer to your configured phone number. A text-based "
        "human handoff is also available for website conversations.",
    },
    {
        "question": "Can I manage multiple businesses?",
        "answer": "Each account is scoped to its own organization. Separate businesses "
        "require separate organizations; agents, numbers, customers and calls stay "
        "isolated between them.",
    },
    {
        "question": "Can I customize how the agent talks?",
        "answer": "Yes. Every agent has configurable instructions, a system prompt, a "
        "greeting, after-hours behavior, recording and transfer settings.",
    },
    {
        "question": "Can I connect my existing phone number?",
        "answer": "Yes. Add your existing number in Phone Numbers and assign it to an agent. "
        "Number porting and provisioning are handled through your Twilio account.",
    },
    {
        "question": "What phone providers are supported?",
        "answer": "Twilio is the supported telephony provider today. Numbers are connected "
        "through your Twilio account from the Phone Numbers page.",
    },
    {
        "question": "How do I install the website widget?",
        "answer": "Create a deployment, copy the generated snippet and paste it into your "
        "HTML before </body>. The snippet auto-loads the widget script for your "
        "deployment.",
    },
]

DEFAULT_NAV = [
    {"label": "Product", "url": "#features"},
    {"label": "Solutions", "url": "#use-cases"},
    {"label": "How it works", "url": "#how-it-works"},
    {"label": "Pricing", "url": "#pricing"},
    {"label": "Resources", "url": "#faq"},
]

DEFAULT_FOOTER = [
    {
        "title": "Product",
        "links": [
            {"label": "AI Agents", "url": "#features"},
            {"label": "Phone", "url": "#phone"},
            {"label": "Website Chat", "url": "#website"},
            {"label": "Appointments", "url": "#features"},
            {"label": "Analytics", "url": "#analytics"},
        ],
    },
    {
        "title": "Solutions",
        "links": [
            {"label": "Small Business", "url": "#use-cases"},
            {"label": "Healthcare", "url": "#use-cases"},
            {"label": "Professional Services", "url": "#use-cases"},
            {"label": "Home Services", "url": "#use-cases"},
        ],
    },
    {
        "title": "Resources",
        "links": [
            {"label": "Documentation", "url": "#"},
            {"label": "API", "url": "#"},
            {"label": "Help Center", "url": "#"},
        ],
    },
    {
        "title": "Company",
        "links": [
            {"label": "About", "url": "#"},
            {"label": "Contact", "url": "#"},
            {"label": "Privacy", "url": "#"},
            {"label": "Terms", "url": "#"},
        ],
    },
]

# Placeholder testimonials are seeded disabled so the landing page never shows
# fabricated social proof until a platform admin adds real content.
DEFAULT_TESTIMONIALS = [
    {
        "name": "Placeholder",
        "company": "Add a real testimonial",
        "role": "Owner",
        "quote": "Replace this testimonial with a real one from the CMS.",
        "enabled": False,
    }
]

DEFAULT_PRICING = [
    {
        "name": "Website",
        "description": "Start with one AI agent on your website. No phone number needed.",
        "price": "Coming soon",
        "billing_period": "",
        "features": ["1 AI agent", "Website chat widget", "Appointment booking", "Basic knowledge base"],
        "cta_text": "Get started",
        "highlighted": False,
    },
    {
        "name": "Growth",
        "description": "Add a business phone number and outbound calling.",
        "price": "Coming soon",
        "billing_period": "",
        "features": ["Everything in Website", "Phone agent", "Outbound calling", "Analytics"],
        "cta_text": "Get started",
        "highlighted": True,
    },
    {
        "name": "Business",
        "description": "For organizations needing multiple agents and channels.",
        "price": "Coming soon",
        "billing_period": "",
        "features": ["More agents", "Advanced knowledge", "Extended analytics"],
        "cta_text": "Contact us",
        "highlighted": False,
    },
    {
        "name": "Enterprise",
        "description": "Custom deployments for larger organizations.",
        "price": "Custom",
        "billing_period": "",
        "features": ["Everything in Business", "Custom configuration", "Dedicated support"],
        "cta_text": "Contact sales",
        "highlighted": False,
    },
]

DEFAULT_PROBLEM_ITEMS = [
    "Missed calls",
    "After-hours inquiries",
    "Repeated questions",
    "Manual appointment booking",
    "Slow lead follow-up",
    "Lost customer context",
]

DEFAULT_VALUE_STRIP = [
    "PHONE",
    "WEBSITE",
    "API",
    "APPOINTMENTS",
    "CUSTOMERS",
    "KNOWLEDGE",
    "ANALYTICS",
]

DEFAULT_STEPS = [
    {
        "num": "01",
        "title": "Create your agent",
        "text": "Define how your AI should speak, behave and represent your business.",
    },
    {
        "num": "02",
        "title": "Connect your business",
        "text": "Add your phone number, website, services and business knowledge.",
    },
    {
        "num": "03",
        "title": "Let it work",
        "text": "Your agent answers customers, handles questions and takes action.",
    },
    {
        "num": "04",
        "title": "See everything",
        "text": "Review calls, customers, appointments and performance from one dashboard.",
    },
]


def seed():
    """Create default CMS content if none exists. Idempotent."""
    if not SiteSettings.objects.exists():
        SiteSettings.objects.load()
    if not LandingPage.objects.exists():
        page = LandingPage.objects.load()
        page.sections = DEFAULT_SECTIONS
        page.is_published = True
        page.value_strip_items = DEFAULT_VALUE_STRIP
        page.problem_items = DEFAULT_PROBLEM_ITEMS
        page.how_works_steps = DEFAULT_STEPS
        page.save()

    _seed_list(FeatureSection, DEFAULT_FEATURES)
    _seed_list(UseCase, DEFAULT_USE_CASES)
    _seed_list(Testimonial, DEFAULT_TESTIMONIALS)
    _seed_list(FAQ, DEFAULT_FAQS)
    _seed_list(NavigationItem, DEFAULT_NAV)
    _seed_list(FooterSection, DEFAULT_FOOTER)
    _seed_list(PricingPlan, DEFAULT_PRICING)
    return True