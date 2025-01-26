import { createStore } from 'vuex'
import api from '../api'

export default createStore({
  state: {
    version: '1.0.5',
    cities: [],
    currentCity: null
  },
  mutations: {
    SET_CITIES(state, cities) {
      state.cities = cities
    },
    SET_CURRENT_CITY(state, city) {
      state.currentCity = city
    }
  },
  actions: {
    async fetchCities({ commit }) {
      try {
        const response = await api.get('/cities')
        commit('SET_CITIES', response.data.cities)
      } catch (error) {
        console.error('Error fetching cities:', error)
        throw error
      }
    }
  },
  modules: {
  }
})
