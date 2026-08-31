import { Link } from 'react-router-dom'

export default function AuthLogo({ brand }) {
  return (
    <Link to="/" className="l-logo" aria-label={`${brand.site_name} home`}>
      <span className="l-logo-mark">A</span>
      {brand.site_name}
    </Link>
  )
}