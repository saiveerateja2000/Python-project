import axios from 'axios'

const usersApi = axios.create({
  baseURL: import.meta.env.VITE_USERS_API_URL || 'http://localhost:5001',
})

const ordersApi = axios.create({
  baseURL: import.meta.env.VITE_ORDERS_API_URL || 'http://localhost:5002',
})

export async function fetchUsers() {
  const { data } = await usersApi.get('/users')
  return data
}

export async function createUser(payload) {
  const { data } = await usersApi.post('/users', payload)
  return data
}

export async function fetchOrders() {
  const { data } = await ordersApi.get('/orders')
  return data
}

export async function createOrder(payload) {
  const { data } = await ordersApi.post('/orders', payload)
  return data
}
