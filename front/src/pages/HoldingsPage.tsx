import { useParams, useNavigate } from 'react-router-dom'
import HoldingsView from '@/components/portfolio/HoldingsView'

export default function HoldingsPage() {
  const { name = 'main' } = useParams()
  const navigate = useNavigate()

  return (
    <HoldingsView
      name={name}
      onViewTransactions={(ticker) => {
        navigate(`/portfolios/${encodeURIComponent(name)}/holdings/transactions?ticker=${encodeURIComponent(ticker)}`)
      }}
    />
  )
}
