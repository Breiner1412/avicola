import { rescueService } from "../api/salvamento.service.js";

class SelectDataManager {
  constructor() {
    this.sheds = [];
    this.chickenTypes = [];
    this.isLoaded = false;
  }

  async loadData() {
    try {
      const [shedsData, chickenTypesData] = await Promise.all([
        rescueService.getSheds(),
        rescueService.getChickenTypes(),
      ]);

      this.sheds = shedsData || [];
      this.chickenTypes = chickenTypesData || [];
      this.isLoaded = true;
    } catch (error) {
      console.error("Error cargando datos para selects:", error);
      this.sheds = [];
      this.chickenTypes = [];
      this.isLoaded = false;
      throw error;
    }
  }

  getShedOptions() {
    return this.sheds.map((shed) => ({
      value: shed.id_galpon,
      text: `${shed.nombre}`,
      data: shed,
    }));
  }

  getChickenTypeOptions() {
    return this.chickenTypes.map((type) => ({
      value: type.id_tipo_gallinas,
      text: type.raza || `Tipo ${type.id_tipo_gallinas}`,
      data: type,
    }));
  }

  getShedById(id) {
    return this.sheds.find((shed) => shed.id_galpon === id);
  }

  getChickenTypeById(id) {
    return this.chickenTypes.find((type) => type.id_tipo_gallinas === id);
  }

  clearCache() {
    this.sheds = [];
    this.chickenTypes = [];
    this.isLoaded = false;
  }
}

export const selectDataManager = new SelectDataManager();
