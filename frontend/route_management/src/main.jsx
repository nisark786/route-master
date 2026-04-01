import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import { store } from './app/store'
import App from './App'
import './index.css'
import 'leaflet/dist/leaflet.css'
import 'react-toastify/dist/ReactToastify.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <App />
        <ToastContainer position="top-right" autoClose={3500} newestOnTop pauseOnFocusLoss={false} />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>
)
