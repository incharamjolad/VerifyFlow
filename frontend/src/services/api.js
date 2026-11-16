import axios from "axios";

const api = axios.create({
  baseURL: "",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vf_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (!window.location.pathname.includes("/login")) {
        localStorage.removeItem("vf_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

