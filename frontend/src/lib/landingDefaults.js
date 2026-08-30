// Offline/default content for the public landing page.
//
// Django is the source of truth via the /public/* CMS API. This module only
// provides graceful degradation when the backend is unreachable or the page
// is unpublished. Its values mirror the seeded CMS content (see
// backend/apps/cms/seed.py) so the design and copy stay in sync.

export const defaultSite = {
  site_name: 'AI Call Agent',
  website_url: '',
  primary_color: '#2E7CF6',
  secondary_color: '#14B8A6',
  font_family: 'Inter',
  logo: '',
  favicon: '',
  social_links: [],
  announcement_enabled: false,
  announcement_text: '',
  meta_title: 'AI Call Agent — Your AI employee for every customer conversation.',
  meta_description:
    'Answer calls, chat with website visitors, book appointments, qualify customers, and hand off to your team automatically.',
}

export const defaultLanding = {
  sections: [
    { key: 'hero', label: 'Hero', enabled: true },
    { key: 'value_strip', label: 'Value strip', enabled: true },
    { key: 'problem', label: 'Problem / solution', enabled: true },
    { key: 'features', label: 'Features', enabled: true },
    { key: 'showcase', label: 'Product showcase', enabled: true },
    { key: 'how_works', label: 'How it works', enabled: true },
    { key: 'website', label: 'Website widget', enabled: true },
    { key: 'phone', label: 'Phone agent', enabled: true },
    { key: 'api', label: 'API', enabled: true },
    { key: 'use_cases', label: 'Use cases', enabled: true },
    { key: 'analytics', label: 'Analytics', enabled: true },
    { key: 'pricing', label: 'Pricing', enabled: true },
    { key: 'faq', label: 'FAQ', enabled: true },
    { key: 'cta', label: 'Final CTA', enabled: true },
  ],
  hero_badge: 'Phone + website AI for service businesses',
  hero_title: 'Your AI employee for every customer conversation.',
  hero_subtitle:
    'Answer calls, chat with website visitors, book appointments, qualify customers, and hand off to your team — automatically.',
  hero_primary_cta: 'Start for free',
  hero_secondary_cta: 'Book a demo',
  value_strip_title: 'One AI agent. Every customer channel.',
  value_strip_items: ['PHONE', 'WEBSITE', 'API', 'APPOINTMENTS', 'CUSTOMERS', 'KNOWLEDGE', 'ANALYTICS'],
  problem_title: "Your team shouldn't have to answer the same questions all day.",
  problem_items: [
    'Missed calls',
    'After-hours inquiries',
    'Repeated questions',
    'Manual appointment booking',
    'Slow lead follow-up',
    'Lost customer context',
  ],
  solution_title: 'Let your AI agent handle the routine. Let your team handle what matters.',
  solution_text:
    'Your AI agent answers the repetitive questions, books appointments, and captures every lead — then hands the conversations that matter to your team.',
  features_title: 'Everything a great receptionist does, on autopilot.',
  features_subtitle: 'Purpose-built tools that turn one AI agent into your busiest employee.',
  showcase_title: 'Everything your AI employee needs to run the conversation.',
  showcase_subtitle:
    'Calls, customers, appointments, agent and analytics — from one clean workspace.',
  how_works_title: 'How it works',
  how_works_steps: [
    {
      num: '01',
      title: 'Create your agent',
      text: 'Define how your AI should speak, behave and represent your business.',
    },
    {
      num: '02',
      title: 'Connect your business',
      text: 'Add your phone number, website, services and business knowledge.',
    },
    {
      num: '03',
      title: 'Let it work',
      text: 'Your agent answers customers, handles questions and takes action.',
    },
    {
      num: '04',
      title: 'See everything',
      text: 'Review calls, customers, appointments and performance from one dashboard.',
    },
  ],
  website_section_title: 'Put your AI agent on your website in minutes.',
  website_section_text: 'Copy one snippet, paste it before </body>, and your agent is live.',
  website_section_cta: 'Create website agent',
  phone_section_title: 'Never miss a customer call again.',
  phone_section_text:
    'Your agent answers, greets, converses, books, and transfers — on your schedule.',
  phone_section_cta: 'Set up phone agent',
  api_section_title: 'Put your AI agent inside your own products.',
  api_section_text:
    'Expose your agent as a conversation API. Custom apps, CRMs and support tools can hand conversations to your AI — no phone number or website needed.',
  api_section_cta: 'Explore the API',
  use_cases_title: 'Built for the way service businesses work.',
  use_cases_subtitle: 'Configure your agent for the questions your customers actually ask.',
  analytics_title: 'Know what happened on every conversation.',
  analytics_subtitle:
    'Conversations, appointments, transfers and outcomes — all in one view.',
  pricing_title: 'Simple pricing for every stage.',
  pricing_subtitle: 'Pricing coming soon. Start free while you set up.',
  pricing_disclaimer: '',
  faq_title: 'Frequently asked questions',
  faq_subtitle: '',
  cta_title: 'Give your business an AI employee.',
  cta_subtitle:
    'Start with one agent. Connect your business. Let it handle the conversations.',
  cta_primary: 'Create your AI agent',
  cta_secondary: 'View demo',
}

export const defaultCollections = {
  features: [
    { id: 'phone', title: 'AI Phone Agent', icon: 'phone', description: 'Answer inbound calls naturally, understand customers, and take action.' },
    { id: 'website', title: 'Website Agent', icon: 'website', description: 'Add an AI assistant to any website with a simple embed snippet.' },
    { id: 'booking', title: 'Appointment Booking', icon: 'calendar', description: 'Check availability and book appointments without human intervention.' },
    { id: 'knowledge', title: 'Business Knowledge', icon: 'knowledge', description: 'Give your agent access to your services, FAQs, documents and business information.' },
    { id: 'memory', title: 'Customer Memory', icon: 'customers', description: "Remember previous conversations so returning customers don't have to repeat themselves." },
    { id: 'transfer', title: 'Human Transfer', icon: 'transfer', description: 'Let AI handle the routine and seamlessly transfer important conversations to your team.' },
    { id: 'analytics', title: 'Call Analytics', icon: 'analytics', description: 'Understand conversations, outcomes, appointments, transfers and customer activity.' },
    { id: 'outbound', title: 'Outbound Calling', icon: 'outbound', description: 'Reach customers proactively when your business needs to.' },
  ],
  useCases: [
    { id: 'dental', title: 'Dental clinics', icon: 'health', description: 'Answer booking questions, confirm appointments and capture patient details.' },
    { id: 'medical', title: 'Medical practices', icon: 'health', description: 'Route routine enquiries and schedule visits without a busy front desk.' },
    { id: 'legal', title: 'Law firms', icon: 'briefcase', description: 'Qualify enquiries, collect intake details and hand off to an attorney.' },
    { id: 'realestate', title: 'Real estate', icon: 'home', description: 'Respond to listing questions and capture qualified buyer or seller leads.' },
    { id: 'salons', title: 'Salons', icon: 'scissors', description: 'Book appointments and answer pricing and availability questions.' },
    { id: 'homeservices', title: 'Home services', icon: 'wrench', description: 'Take service requests, answer FAQs and schedule visits — day or night.' },
    { id: 'restaurants', title: 'Restaurants', icon: 'restaurant', description: 'Take reservations and answer hours, menu and location questions.' },
    { id: 'automotive', title: 'Automotive', icon: 'car', description: 'Book service visits and answer pricing, warranty and hours questions.' },
    { id: 'professionalservices', title: 'Professional services', icon: 'briefcase', description: 'Capture enquiries and book consultations without a receptionist.' },
    { id: 'consulting', title: 'Consulting', icon: 'briefcase', description: 'Capture enquiries, gather project details and book discovery calls.' },
    { id: 'smallbusiness', title: 'Small business', icon: 'store', description: 'One agent that never misses a call, however small your team is.' },
  ],
  testimonials: [],
  pricing: [
    { name: 'Starter', description: 'For small businesses getting started with one agent.', price: 'Coming soon', billing_period: '', features: ['1 AI agent', 'Phone and website channels', 'Appointment booking'], cta_text: 'Get started', highlighted: false },
    { name: 'Growth', description: 'For growing teams that need more capacity.', price: 'Coming soon', billing_period: '', features: ['Multiple agents', 'Outbound calling', 'Knowledge base', 'Analytics'], cta_text: 'Get started', highlighted: true },
    { name: 'Business', description: 'For organizations needing multiple agents and channels.', price: 'Coming soon', billing_period: '', features: ['More agents', 'Advanced knowledge', 'Extended analytics'], cta_text: 'Contact us', highlighted: false },
    { name: 'Enterprise', description: 'Custom deployments for larger organizations.', price: 'Custom', billing_period: '', features: ['Everything in Business', 'Custom configuration', 'Dedicated support'], cta_text: 'Contact sales', highlighted: false },
  ],
  faqs: [
    { question: 'What is an AI business agent?', answer: 'An AI business agent answers calls and website chats for your business — understanding questions, booking appointments, sharing your services and knowledge, and handing conversations to humans when needed.' },
    { question: 'Can it answer phone calls?', answer: 'Yes. Once a phone number is connected and assigned to an agent, inbound calls are answered automatically and outbound calls can be placed from the dashboard.' },
    { question: 'Can it work on my website?', answer: 'Yes. Create a website deployment, copy the snippet, and paste it before </body> on your site.' },
    { question: 'Can it book appointments?', answer: 'Yes. With services and availability configured, the agent checks the calendar and books through the backend so it never promises a slot that conflicts.' },
    { question: 'Can I give it my business knowledge?', answer: 'Yes. A knowledge base can be attached to each agent and populated with documents (PDFs and text).' },
    { question: 'Can it transfer calls to employees?', answer: 'Yes. The agent can transfer to your configured phone number, with a text-based handoff also available for website conversations.' },
    { question: 'Can I manage multiple businesses?', answer: 'Each account is scoped to its own organization. Agents, numbers, customers and calls stay isolated between organizations.' },
    { question: 'Can I customize how the agent talks?', answer: 'Yes. Every agent has configurable instructions, a system prompt, greeting, after-hours behavior, recording and transfer settings.' },
    { question: 'What phone providers are supported?', answer: 'Twilio is the supported telephony provider today; numbers are connected through your Twilio account.' },
    { question: 'Can I connect my existing phone number?', answer: 'Yes. Add your existing number in Phone Numbers and assign it to an agent. Number porting and provisioning are handled through your Twilio account.' },
    { question: 'How do I install the website widget?', answer: 'Create a deployment, copy the generated snippet and paste it into your HTML before </body>.' },
  ],
  nav: [
    { label: 'Product', url: '#features' },
    { label: 'Solutions', url: '#use-cases' },
    { label: 'How it works', url: '#how-it-works' },
    { label: 'Pricing', url: '#pricing' },
    { label: 'Resources', url: '#faq' },
  ],
  footer: [
    { title: 'Product', links: [{ label: 'AI Agents', url: '#features' }, { label: 'Phone', url: '#phone' }, { label: 'Website Chat', url: '#website' }, { label: 'Appointments', url: '#features' }, { label: 'Analytics', url: '#analytics' }] },
    { title: 'Solutions', links: [{ label: 'Small Business', url: '#use-cases' }, { label: 'Healthcare', url: '#use-cases' }, { label: 'Professional Services', url: '#use-cases' }, { label: 'Home Services', url: '#use-cases' }] },
    { title: 'Resources', links: [{ label: 'Documentation', url: '#' }, { label: 'API', url: '#' }, { label: 'Help Center', url: '#' }] },
    { title: 'Company', links: [{ label: 'About', url: '#' }, { label: 'Contact', url: '#' }, { label: 'Privacy', url: '#' }, { label: 'Terms', url: '#' }] },
  ],
}

export function mergeCms(site, landing, collections) {
  // Fill gaps from defaults so partial API failures degrade gracefully.
  return {
    site: { ...defaultSite, ...(site || {}) },
    landing: { ...defaultLanding, ...(landing || {}) },
    features: collections.features && collections.features.length ? collections.features : defaultCollections.features,
    useCases: collections.useCases && collections.useCases.length ? collections.useCases : defaultCollections.useCases,
    testimonials: collections.testimonials || [],
    pricing: collections.pricing && collections.pricing.length ? collections.pricing : defaultCollections.pricing,
    faqs: collections.faqs && collections.faqs.length ? collections.faqs : defaultCollections.faqs,
    nav: collections.nav && collections.nav.length ? collections.nav : defaultCollections.nav,
    footer: collections.footer && collections.footer.length ? collections.footer : defaultCollections.footer,
  }
}

export function landingCopySubset(landing) {
  // Public landing-page response is a plain JSON object; keep as-is.
  return landing || {}
}