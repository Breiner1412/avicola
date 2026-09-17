const mainContent = document.getElementById("main-content");
const navLinks = document.querySelector(".app-nav");

// Oculta los ítems de menú según rol usando permisos.js si está cargado
function applyMenuPermissions() {
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  const role = (user?.nombre_rol || "").toLowerCase();

  // Fallback local si no está disponible tienePermiso
  const fallback = {
    superadmin: [
      "users",
      "alimentos",
      "consumo_alimento",
      "tareas",
      "galpones",
      "incidentes",
      "inventario",
      "registro_sensores",
      "incidentes_gallina",
      "chickens",
      "tipos_gallinas",
      "rescue",
      "produccion_huevos",
      "stock",
      "ventas",
    ],
    administrador: [
      "users",
      "alimentos",
      "consumo_alimento",
      "tareas",
      "galpones",
      "incidentes",
      "inventario",
      "registro_sensores",
      "incidentes_gallina",
      "chickens",
      "tipos_gallinas",
      "rescue",
      "produccion_huevos",
      "stock",
      "ventas",
    ],
    supervisor: [
      "tareas",
      "alimentos",
      "consumo_alimento",
      "incidentes",
      "registro_sensores",
      "tipos_gallinas",
      "rescue",
      "chickens",
      "incidentes_gallina",
      "produccion_huevos",
      "stock",
    ],
    operario: [
      "tareas",
      "galpones",
      "alimentos",
      "consumo_alimento",
      "incidentes",
      "registro_sensores",
      "tipos_gallinas",
      "rescue",
      "chickens",
      "incidentes_gallina",
      "produccion_huevos",
      "stock",
    ],
  };

  const canView = (page) => {
    if (page === "panel") return true;
    if (typeof window.tienePermiso === "function") {
      return window.tienePermiso(page, "ver");
    }
    const allowed = fallback[role];
    return !!(allowed && allowed.includes(page));
  };

  document.querySelectorAll("a[data-page]").forEach((link) => {
    const page = link.getAttribute("data-page");
    if (!page || page === "panel") return;
    if (!canView(page)) {
      const li = link.closest("li.nav-item");
      if (li) li.style.display = "none";
    }
  });

  [
    "submenu-usuario",
    "submenu-monitoreo",
    "submenu-gallinas",
    "submenu-producción",
    "submenu-alimentos",
  ].forEach((submenuId) => {
    const submenu = document.getElementById(submenuId);
    if (!submenu) return;
    const visibles = Array.from(submenu.querySelectorAll("li.nav-item")).filter(
      (li) => li.style.display !== "none"
    );
    if (visibles.length === 0) {
      const wrapper = submenu.closest("li.nav-item.has-submenu");
      if (wrapper) wrapper.style.display = "none";
    }
  });
}

const loadContent = async (page) => {
  if (!mainContent) return;
  // Página actual (la usan los módulos para saber si deben responder a eventos globales)
  window.currentPage = page;
  try {
    const response = await fetch(`pages/${page}.html`);
    if (!response.ok) {
      // Si la respuesta no es OK, lanzamos un error para que lo capture el catch.
      throw new Error(
        `Error de red: ${response.status} - ${response.statusText}`
      );
    }
    const html = await response.text();
    // Si mientras cargaba se eligió otra página, se descarta esta respuesta
    if (window.currentPage !== page) return;
    mainContent.innerHTML = html;
    // Aplicar permisos después de cargar contenido
    if (typeof window.aplicarPermisos === "function") {
      setTimeout(() => window.aplicarPermisos(page), 50);
    }

    //  // Actualizar clase active en el menú
    // updateActiveMenuItem(page);

    // Módulo JS de cada página (se importa una sola vez y se llama a init()
    // en cada visita; los módulos ya NO se auto-inicializan al importarse)
    const modulosPorPagina = {
      aislamientos: ["./pages/isolations.js"],
      incidentes_gallina: ["./pages/incident_chicken.js"],
      chickens: ["./pages/chickens.js"],
      rescue: ["./pages/rescue.js"],
      tipos_gallinas: ["./pages/tipos_gallinas.js"],
      incidentes: ["./pages/incidentes.js"],
      galpones: ["./pages/sheds.js"],
      categorias_inventario: ["./pages/categories_inventory.js"],
      inventario: ["./pages/inventory.js"],
      sensors: ["./pages/sensors.js"],
      sensor_types: ["./pages/sensor_types.js"],
      registro_sensores: ["./pages/registro-sensores.js"],
      lands: ["./pages/lands.js"],
      panel: ["./pages/panel.js"],
      produccion_huevos: ["./pages/produccionHuevos.js", "./pages/tipoHuevos.js"],
      roles: ["./pages/roles.js"],
      users: ["./pages/users.js"],
      metodos_pago: ["./pages/metodo_pago.js"],
      detalles_venta: ["./pages/detalles_venta.js"],
      tareas: ["./pages/tareas.js"],
      ventas: ["./pages/ventas.js"],
      info_venta: ["./pages/info_venta.js"],
      perfil: ["./pages/perfil.js"],
      alimentos: ["./pages/alimentos.js"],
      consumo_alimento: ["./pages/consumo_alimento.js"],
      stock: ["./pages/stock.js"],
    };

    for (const ruta of modulosPorPagina[page] || []) {
      try {
        const modulo = await import(ruta);
        // Si el usuario ya navegó a otra página mientras cargaba, no inicializar
        if (window.currentPage !== page) return;
        await modulo.init();
      } catch (err) {
        console.error(`Error al cargar el módulo ${ruta}:`, err);
      }
    }

  } catch (error) {
    console.error("¡ERROR! Algo falló dentro de loadContent:", error);
    mainContent.innerHTML = `<h3 class="text-center text-danger p-5">No se pudo cargar el contenido. Revisa la consola (F12).</h3>`;
  }
};

navLinks?.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-page]");

  if (link) {
    event.preventDefault();
    const pageToLoad = link.dataset.page;
    loadContent(pageToLoad);

    // const sidepanel = document.getElementById('app-sidepanel');
    // if (sidepanel && window.innerWidth < 1200) {
    //   sidepanel.classList.remove('sidepanel-visible');
    //   sidepanel.classList.add('sidepanel-hidden');
    // }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  applyMenuPermissions();
  loadContent("panel");
});

const logoutButton = document.getElementById("logout-button");

if (logoutButton) {
  logoutButton.addEventListener("click", (event) => {
    event.preventDefault();
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    window.location.href = "index.html";
  });
}

// Delegación global para accesos directos del panel
document.addEventListener("click", (e) => {
  const shortcut = e.target.closest(".shortcut-link[data-page]");
  if (shortcut) {
    e.preventDefault();
    const page = shortcut.dataset.page;
    loadContent(page);
  }
});
const buttonPerfil = document.getElementById("buttonPerfil");
if (buttonPerfil) {
  buttonPerfil.addEventListener("click", () => {
    const pageValue = buttonPerfil.dataset.page;
    if (pageValue) loadContent(pageValue);
  });
}
// para  llamar pagnas dentro de paginas
window.loadContent = loadContent;
