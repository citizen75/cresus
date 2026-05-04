export default function Spinner() {
  return (
    <div className="flex items-center justify-center">
      <div className="relative w-8 h-8">
        <div className="absolute inset-0 border-2 border-slate-700 rounded-full"></div>
        <div className="absolute inset-0 border-2 border-transparent border-t-purple-600 rounded-full animate-spin"></div>
      </div>
    </div>
  )
}
