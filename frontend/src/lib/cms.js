import { api } from '../api'
import { defaultCollections, defaultLanding, defaultSite, mergeCms } from './landingDefaults'

const ENDPOINTS = [
  ['site', '/public/site-config'],
  ['landing', '/public/landing-page'],
  ['features', '/public/features'],
  ['useCases', '/public/use-cases'],
  ['testimonials', '/public/testimonials'],
  ['pricing', '/public/pricing'],
  ['faqs', '/public/faqs'],
  ['nav', '/public/navigation'],
  ['footer', '/public/footer'],
]

export async function loadPublicSite() {
  const data = {}
  for (const [key, path] of ENDPOINTS) {
    try {
      data[key] = await api.get(path)
    } catch {
      // Offline or unpublished section → fall back to defaults for that piece.
      data[key] = null
    }
  }

  const site = data.site || defaultSite
  const landing = data.landing || defaultLanding
  const collections = {
    features: data.features || defaultCollections.features,
    useCases: data.useCases || defaultCollections.useCases,
    testimonials: data.testimonials || [],
    pricing: data.pricing || defaultCollections.pricing,
    faqs: data.faqs || defaultCollections.faqs,
    nav: data.nav || defaultCollections.nav,
    footer: data.footer || defaultCollections.footer,
  }

  const merged = mergeCms(site, landing, collections)
  merged.backend = Boolean(data.site && data.landing)
  return merged
}