import { useEffect, useState } from 'react'
import { createOrder, createUser, fetchOrders, fetchUsers } from './api'

export default function App() {
  const [users, setUsers] = useState([])
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')

  const [userForm, setUserForm] = useState({ name: '', email: '' })
  const [orderForm, setOrderForm] = useState({ user_id: '', item: '', quantity: 1 })

  const loadData = async () => {
    try {
      setError('')
      const [usersData, ordersData] = await Promise.all([fetchUsers(), fetchOrders()])
      setUsers(usersData)
      setOrders(ordersData)
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.message)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreateUser = async (event) => {
    event.preventDefault()
    try {
      await createUser(userForm)
      setUserForm({ name: '', email: '' })
      await loadData()
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.message)
    }
  }

  const handleCreateOrder = async (event) => {
    event.preventDefault()
    try {
      await createOrder({
        user_id: Number(orderForm.user_id),
        item: orderForm.item,
        quantity: Number(orderForm.quantity),
      })
      setOrderForm({ user_id: '', item: '', quantity: 1 })
      await loadData()
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.message)
    }
  }

  return (
    <main>
      <h1>Cloud Native Project - Stage 1 (Local)</h1>
      {error && <p className="error">Error: {error}</p>}

      <section>
        <h2>Create User</h2>
        <form onSubmit={handleCreateUser}>
          <input
            placeholder="Name"
            value={userForm.name}
            onChange={(event) => setUserForm((prev) => ({ ...prev, name: event.target.value }))}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={userForm.email}
            onChange={(event) => setUserForm((prev) => ({ ...prev, email: event.target.value }))}
            required
          />
          <button type="submit">Add User</button>
        </form>
      </section>

      <section>
        <h2>Create Order</h2>
        <form onSubmit={handleCreateOrder}>
          <select
            value={orderForm.user_id}
            onChange={(event) => setOrderForm((prev) => ({ ...prev, user_id: event.target.value }))}
            required
          >
            <option value="">Select User</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name} ({user.email})
              </option>
            ))}
          </select>
          <input
            placeholder="Item"
            value={orderForm.item}
            onChange={(event) => setOrderForm((prev) => ({ ...prev, item: event.target.value }))}
            required
          />
          <input
            type="number"
            min="1"
            value={orderForm.quantity}
            onChange={(event) => setOrderForm((prev) => ({ ...prev, quantity: event.target.value }))}
            required
          />
          <button type="submit">Create Order</button>
        </form>
      </section>

      <section>
        <h2>Users</h2>
        <ul>
          {users.map((user) => (
            <li key={user.id}>{user.name} - {user.email}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Orders</h2>
        <ul>
          {orders.map((order) => (
            <li key={order.id}>
              User #{order.user_id} ordered {order.quantity} x {order.item} ({order.status})
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
