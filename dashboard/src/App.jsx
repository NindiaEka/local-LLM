import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Analytics from './pages/Analytics'
import ApiKeys from './pages/ApiKeys'
import Dashboard from './pages/Dashboard'
import Models from './pages/Models'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="apikeys" element={<ApiKeys />} />
          <Route path="models" element={<Models />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
