import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '', // Handled by Vite proxy
  timeout: 10000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error", error);
    const message = error.response?.data?.detail || error.message;
    return Promise.reject(new Error(message));
  }
);
