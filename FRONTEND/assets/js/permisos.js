// Sistema simple de permisos para botones
(function () {
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  const rol = user.nombre_rol ? user.nombre_rol.toLowerCase() : "";

  // Variable global para guardar el módulo actual
  window._currentModule = null;

  // Permisos por rol y módulo (C=crear, E=editar, D=eliminar)
  const permisos = {
    superadmin: {
      users: { ver: true, crear: true, editar: true, eliminar: true },
      roles: { ver: true, crear: true, editar: true, eliminar: true },
      tareas: { ver: true, crear: true, editar: true, eliminar: true },
      lands: { ver: true, crear: true, editar: true, eliminar: true },
      galpones: { ver: true, crear: true, editar: true, eliminar: true },
      incidentes: { ver: true, crear: true, editar: true, eliminar: true },
      inventario: { ver: true, crear: true, editar: true, eliminar: true },
      sensors: { ver: true, crear: true, editar: true, eliminar: true },
      sensor_types: { ver: true, crear: true, editar: true, eliminar: true },
      registro_sensores: {
        ver: true,
        crear: false,
        editar: false,
        eliminar: false,
      },
      incidentes_gallina: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      chickens: { ver: true, crear: true, editar: true, eliminar: true },
      tipos_gallinas: { ver: true, crear: true, editar: true, eliminar: true },
      rescue: { ver: true, crear: true, editar: true, eliminar: true },
      aislamientos: { ver: true, crear: true, editar: true, eliminar: true },
      produccion_huevos: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      stock: { ver: true, crear: true, editar: true, eliminar: true },
      ventas: { ver: true, crear: true, editar: true, eliminar: true },
      alimento: { ver: true, crear: true, editar: true, eliminar: true },
      metodo_pago: { ver: true, crear: true, editar: true, eliminar: true },
      categoria_inventario: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      tipo_huevos: { ver: true, crear: true, editar: true, eliminar: true },
      modulos: { ver: true, crear: true, editar: true, eliminar: true },
      permisos: { ver: true, crear: true, editar: true, eliminar: true },
      alimentos: { ver: true, crear: true, editar: true, eliminar: true },
      consumo_gallinas: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
    },
    administrador: {
      users: { ver: true, crear: true, editar: true, eliminar: true },
      roles: { ver: true, crear: true, editar: true, eliminar: true },
      tareas: { ver: true, crear: true, editar: true, eliminar: true },
      lands: { ver: true, crear: true, editar: true, eliminar: true },
      galpones: { ver: true, crear: true, editar: true, eliminar: true },
      incidentes: { ver: true, crear: true, editar: true, eliminar: true },
      inventario: { ver: true, crear: true, editar: true, eliminar: true },
      sensors: { ver: true, crear: true, editar: true, eliminar: false },
      sensor_types: { ver: true, crear: true, editar: true, eliminar: false },
      registro_sensores: {
        ver: true,
        crear: false,
        editar: false,
        eliminar: false,
      },
      incidentes_gallina: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      chickens: { ver: true, crear: true, editar: true, eliminar: true },
      tipos_gallinas: { ver: true, crear: true, editar: true, eliminar: true },
      rescue: { ver: true, crear: true, editar: true, eliminar: true },
      aislamientos: { ver: true, crear: true, editar: true, eliminar: true },
      produccion_huevos: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      stock: { ver: true, crear: true, editar: true, eliminar: true },
      ventas: { ver: true, crear: true, editar: true, eliminar: true },
      alimento: { ver: true, crear: true, editar: true, eliminar: true },
      metodo_pago: { ver: true, crear: true, editar: true, eliminar: true },
      categoria_inventario: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: true,
      },
      tipo_huevos: { ver: true, crear: true, editar: true, eliminar: true },
      modulos: { ver: true, crear: true, editar: true, eliminar: false },
      permisos: { ver: true, crear: true, editar: true, eliminar: false },
      alimentos: { ver: true, crear: true, editar: true, eliminar: false },
      consumo_gallinas: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
    },
    supervisor: {
      users: { ver: false, crear: false, editar: false, eliminar: false },
      roles: { ver: false, crear: false, editar: false, eliminar: false },
      tareas: { ver: true, crear: true, editar: true, eliminar: true },
      lands: { ver: false, crear: false, editar: false, eliminar: false },
      galpones: { ver: true, crear: false, editar: false, eliminar: false },
      incidentes: { ver: true, crear: true, editar: true, eliminar: true },
      inventario: { ver: false, crear: false, editar: false, eliminar: false },
      sensors: { ver: true, crear: true, editar: true, eliminar: false },
      sensor_types: { ver: true, crear: true, editar: true, eliminar: false },
      registro_sensores: {
        ver: true,
        crear: false,
        editar: false,
        eliminar: false,
      },
      incidentes_gallina: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
      chickens: { ver: true, crear: true, editar: true, eliminar: false },
      tipos_gallinas: { ver: true, crear: true, editar: true, eliminar: false },
      rescue: { ver: true, crear: true, editar: true, eliminar: false },
      aislamientos: { ver: true, crear: true, editar: false, eliminar: false },
      produccion_huevos: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
      stock: { ver: true, crear: true, editar: true, eliminar: false },
      ventas: { ver: false, crear: false, editar: false, eliminar: false },
      alimento: { ver: false, crear: false, editar: false, eliminar: false },
      metodo_pago: { ver: false, crear: false, editar: false, eliminar: false },
      categoria_inventario: {
        ver: false,
        crear: false,
        editar: false,
        eliminar: false,
      },
      tipo_huevos: { ver: true, crear: false, editar: false, eliminar: false },
      modulos: { ver: false, crear: false, editar: false, eliminar: false },
      permisos: { ver: false, crear: false, editar: false, eliminar: false },
      alimentos: { ver: true, crear: true, editar: true, eliminar: false },
      consumo_gallinas: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
    },
    operario: {
      users: { ver: false, crear: false, editar: false, eliminar: false },
      roles: { ver: false, crear: false, editar: false, eliminar: false },
      tareas: { ver: true, crear: false, editar: true, eliminar: false },
      lands: { ver: false, crear: false, editar: false, eliminar: false },
      galpones: { ver: true, crear: false, editar: false, eliminar: false },
      incidentes: { ver: true, crear: false, editar: true, eliminar: false },
      inventario: { ver: false, crear: false, editar: false, eliminar: false },
      sensors: { ver: false, crear: false, editar: false, eliminar: false },
      sensor_types: {
        ver: false,
        crear: false,
        editar: false,
        eliminar: false,
      },
      registro_sensores: {
        ver: true,
        crear: false,
        editar: false,
        eliminar: false,
      },
      incidentes_gallina: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
      chickens: { ver: true, crear: true, editar: true, eliminar: false },
      tipos_gallinas: {
        ver: true,
        crear: false,
        editar: false,
        eliminar: false,
      },
      rescue: { ver: true, crear: true, editar: true, eliminar: false },
      aislamientos: { ver: true, crear: true, editar: false, eliminar: false },
      produccion_huevos: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
      stock: { ver: true, crear: true, editar: false, eliminar: false },
      ventas: { ver: false, crear: false, editar: false, eliminar: false },
      alimento: { ver: false, crear: false, editar: false, eliminar: false },
      metodo_pago: { ver: false, crear: false, editar: false, eliminar: false },
      categoria_inventario: {
        ver: false,
        crear: false,
        editar: false,
        eliminar: false,
      },
      tipo_huevos: { ver: true, crear: false, editar: false, eliminar: false },
      modulos: { ver: false, crear: false, editar: false, eliminar: false },
      permisos: { ver: false, crear: false, editar: false, eliminar: false },
      alimentos: { ver: true, crear: false, editar: false, eliminar: false },
      consumo_gallinas: {
        ver: true,
        crear: true,
        editar: true,
        eliminar: false,
      },
    },
  };

  // Función para verificar permiso
  // Algunos data-page del menú no coinciden con las claves de arriba
  const alias = {
    categorias_inventario: "categoria_inventario",
    metodos_pago: "metodo_pago",
    consumo_alimento: "consumo_gallinas",
    detalles_venta: "ventas",
    info_venta: "ventas",
    perfil: null,
  };

  window.tienePermiso = function (modulo, accion) {
    if (modulo === "perfil" || modulo === "panel") return true;
    if (!rol || !permisos[rol]) return false;
    const clave = permisos[rol][modulo] ? modulo : alias[modulo];
    if (!clave || !permisos[rol][clave]) return false;
    return permisos[rol][clave][accion] || false;
  };

  // Aplicar permisos cuando el DOM esté listo
  document.addEventListener("DOMContentLoaded", function () {
    aplicarPermisos();
  });

  // Determinar el módulo actual según el enlace activo o el título
  function obtenerModuloActual() {
    const activeLink = document.querySelector("a[data-page].active");
    if (activeLink) return activeLink.getAttribute("data-page");

    const allLinks = document.querySelectorAll("a[data-page]");
    let lastPage = null;
    allLinks.forEach((link) => {
      const page = link.getAttribute("data-page");
      if (page) lastPage = page;
    });
    if (lastPage) return lastPage;

    const pageTitle = document.querySelector(
      "#main-content h4, #main-content h1"
    );
    if (pageTitle) {
      const texto = pageTitle.textContent.toLowerCase().trim();
      const mapeo = {
        panel: "panel",
        usuarios: "users",
        roles: "roles",
        tareas: "tareas",
        fincas: "lands",
        galpones: "galpones",
        incidentes: "incidentes",
        "inventario finca": "inventario",
        sensores: "sensors",
        "tipos de sensores": "sensor_types",
        "registros de sensores": "registro_sensores",
        "incidente gallina": "incidentes_gallina",
        "registro gallinas": "chickens",
        "tipos de gallinas": "tipos_gallinas",
        salvamento: "rescue",
        aislamientos: "aislamientos",
        "produccion huevos": "produccion_huevos",
        stock: "stock",
        ventas: "ventas",
      };
      return mapeo[texto] || null;
    }

    return null;
  }

  // También exponer para llamar manualmente después de cargar contenido dinámico
  window.aplicarPermisos = function (modulo = null) {
    // Si se pasa un módulo explícitamente, guardarlo
    if (modulo) {
      window._currentModule = modulo;
    }

    const paginaActual =
      modulo || window._currentModule || obtenerModuloActual();

    if (!paginaActual) {
      console.warn("No se pudo detectar el módulo actual");
      return;
    }

    // Ocultar shortcuts del panel según permisos
    if (paginaActual === "panel") {
      document.querySelectorAll(".shortcut-link[data-page]").forEach((link) => {
        const targetPage = link.getAttribute("data-page");
        if (targetPage && !tienePermiso(targetPage, "ver")) {
          link.style.display = "none";
        }
      });
    }

    // Ocultar botones de crear
    if (!tienePermiso(paginaActual, "crear")) {
      document
        .querySelectorAll(
          '[data-action="create"], [id*="btn-open-create"], [id*="create-"], .btn:has(i.fa-plus)'
        )
        .forEach((btn) => {
          if (btn.tagName === "BUTTON" || btn.classList.contains("btn")) {
            btn.style.display = "none";
          }
        });
    }

    // Ocultar botones de editar
    if (!tienePermiso(paginaActual, "editar")) {
      document
        .querySelectorAll('[data-action="edit"], .btn-edit, [onclick*="edit"]')
        .forEach((btn) => {
          btn.style.display = "none";
        });
    }

    // Ocultar botones de eliminar
    if (!tienePermiso(paginaActual, "eliminar")) {
      document
        .querySelectorAll(
          '[data-action="delete"], .btn-delete, [onclick*="delete"]'
        )
        .forEach((btn) => {
          btn.style.display = "none";
        });
    }
    document.querySelectorAll("[data-required-module]").forEach((btn) => {
      const requiredModule = btn.getAttribute("data-required-module");
      const requiredAction = btn.getAttribute("data-required-action") || "ver";

      if (!tienePermiso(requiredModule, requiredAction)) {
        btn.style.display = "none";
      }
    });
  };

  // Función específica para ocultar rol superadmin en selects
  function ocultarOpcionSuperadmin() {
    setTimeout(() => {
      document
        .querySelectorAll('select[id*="rol"], select[id*="id_rol"]')
        .forEach((select) => {
          const option = select.querySelector('option[value="1"]');
          if (option) option.style.display = "none";
        });
    }, 100);
  }
})();
