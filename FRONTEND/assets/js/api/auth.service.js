// Este servicio NO usará nuestro apiClient 'request' porque el login es especial (x-www-form-urlencoded)
// y no necesita token.

export const authService = {
  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    window.location.href = "index.html";
  },
};
