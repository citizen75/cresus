import { useParams, useSearchParams, Link } from 'react-router-dom'
import TransactionsView from '@/components/portfolio/TransactionsView'

export default function TransactionsPage() {
  const { name = 'main' } = useParams()
  const [searchParams] = useSearchParams()
  const filterTicker = searchParams.get('ticker') || undefined

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
        <Link
          to={`/portfolios/${encodeURIComponent(name)}/holdings`}
          className="text-purple-400 hover:text-purple-300 text-sm font-medium"
        >
          ← Back to Holdings
        </Link>
        <h1 className="text-2xl font-bold text-white">
          Transactions
          {filterTicker && <span className="text-slate-400 font-normal ml-2">({filterTicker})</span>}
        </h1>
      </div>
      <TransactionsView name={name} filterTicker={filterTicker} />
    </div>
  )
}
