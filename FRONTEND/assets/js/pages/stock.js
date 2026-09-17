import ApexCharts from "../../plugins/apexcharts/apexcharts.esm.js";
import { stockService } from "../api/stock.service.js";

// Nombre legible del tipo de huevo
function nombreTipo(tipo) {
  return tipo == 1 ? "AA" : tipo == 2 ? "AAA" : tipo == 3 ? "Super" : "";
}

// ----------------------------
// Crear fila de la tabla
// ----------------------------
function createStockRow(stock) {
  return `
    <tr>
        <td>${nombreTipo(stock.tipo)}</td>
        <td>${stock.unidad_medida}</td>
        <td>${stock.nombre_producto}</td>
        <td>${stock.cantidad_disponible}</td>
    </tr>
  `;
}

// ----------------------------
// Función principal INIT (una sola petición para tabla y gráficas)
// ----------------------------
export async function init() {
  const tbody = document.getElementById("stock-table-body");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="4" class="text-center">Cargando...</td></tr>`;

  let stocks = [];
  try {
    stocks = (await stockService.GetStockAll()) || [];
  } catch (error) {
    console.error("Error cargando stock:", error);
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center">Error al cargar datos.</td></tr>`;
    return;
  }

  tbody.innerHTML = stocks.length
    ? stocks.map(createStockRow).join("")
    : `<tr><td colspan="4" class="text-center">No hay registros.</td></tr>`;

  if (stocks.length === 0) {
    const mayor = document.getElementById("productoMayor");
    const menor = document.getElementById("productoMenor");
    if (mayor) mayor.textContent = "Sin datos de stock.";
    if (menor) menor.textContent = "";
    return;
  }

  // Esperar a que el contenedor tenga tamaño antes de dibujar
  requestAnimationFrame(() => {
    if (window.currentPage !== "stock") return;
    renderChart(stocks);
    renderDonutChart(stocks);
  });
}

////////////////////////////////
////////  GRAFICAS *************
//////////////////////////////

function renderChart(stocks) {

  if (!stocks || stocks.length === 0) {
    return;
  }

  // 2️⃣ Crear etiquetas tipo "Nombre (Unidad/Tipo)"
  const labels = stocks.map((s) => {
    const tipo = nombreTipo(s.tipo);
    return `${s.nombre_producto} (${tipo || s.unidad_medida})`;
  });

  // 3️⃣ Cantidades de stock disponible
  const cantidades = stocks.map((s) => s.cantidad_disponible);

  // 4️⃣ Detectar producto mayor y menor
  const mayor = stocks.reduce((max, s) =>
    s.cantidad_disponible > max.cantidad_disponible ? s : max
  );
  const menor = stocks.reduce((min, s) =>
    s.cantidad_disponible < min.cantidad_disponible ? s : min
  );

  document.getElementById(
    "productoMayor"
  ).textContent = `Producto con mayor stock: ${mayor.nombre_producto} (${mayor.cantidad_disponible} unidades)`;

  document.getElementById(
    "productoMenor"
  ).textContent = `Producto con menor stock: ${menor.nombre_producto} (${menor.cantidad_disponible} unidades)`;

  // 5️⃣ Calcular promedio
  const promedio = Math.round(
    cantidades.reduce((a, b) => a + b, 0) / cantidades.length
  );
  const promedioSeries = cantidades.map(() => promedio);
  // 6️⃣ Configurar gráfica (solo 2 líneas: Stock y Promedio)
  const chartDiv = document.querySelector("#chart");
  if (!chartDiv) return;

  const options = {
    series: [
      {
        name: "Stock disponible",
        data: cantidades,
      },
      {
        name: "Promedio de stock",
        data: promedioSeries,
      },
    ],
    chart: { type: "bar", height: 350 },
    plotOptions: {
      bar: { horizontal: false, columnWidth: "55%", borderRadius: 5 },
    },
    dataLabels: { enabled: false },
    stroke: { show: true, width: 2, colors: ["transparent"] },
    colors: ["#2980b9", "#1ec882"],
    xaxis: {
      categories: labels,
      labels: { rotate: -45, style: { fontSize: "13px" } },
    },
    yaxis: {
      title: { text: "Cantidad (unidades)" },
      labels: { formatter: (value) => value.toFixed(0) },
    },
    fill: { opacity: 1 },
    tooltip: { y: { formatter: (val) => val + " unidades" } },
  };

  chartDiv.innerHTML = "";
  const chart = new ApexCharts(chartDiv, options);
  chart.render();
}

function renderDonutChart(stocks) {

  if (!stocks || stocks.length === 0) {
    return;
  }

  // 2️⃣ Etiquetas tipo "Nombre (Tipo/Unidad)"
  const labels = stocks.map((s) => {
    const tipo = nombreTipo(s.tipo);
    const extra = tipo || s.unidad_medida;
    return extra ? `${s.nombre_producto} (${extra})` : s.nombre_producto;
  });

  // 3️⃣ Cantidades de stock (validar números)
  const cantidades = stocks.map((s) => {
    const cantidad = parseFloat(s.cantidad_disponible);
    return isNaN(cantidad) ? 0 : cantidad;
  });

  // 4️⃣ Configurar gráfica dona
  const chartDiv = document.querySelector("#donutChart");
  if (!chartDiv) return;

  // Validar que hay datos válidos antes de renderizar
  const total = cantidades.reduce((a, b) => a + b, 0);
  if (total === 0 || isNaN(total)) {
    chartDiv.innerHTML =
      '<p class="text-center text-muted">No hay datos disponibles para mostrar</p>';
    return;
  }

  const options = {
    colors: ["#2980b9", "#1ec882", "#e74c3c", "#f39c12", "#9b59b6"],
    series: cantidades,
    chart: {
      type: "donut",
      height: 350,
    },
    labels: labels,
    legend: {
      position: "right",
      fontSize: "18px",
    },
    tooltip: {
      y: {
        formatter: (val) => val + " unidades",
      },
    },
    plotOptions: {
      pie: {
        donut: {
          size: "60%",
          labels: {
            show: true,
            total: {
              show: true,
              label: "Total",
              formatter: function (w) {
                return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
              },
            },
          },
        },
      },
    },
  };

  chartDiv.innerHTML = "";
  const chart = new ApexCharts(chartDiv, options);
  chart.render();
}
