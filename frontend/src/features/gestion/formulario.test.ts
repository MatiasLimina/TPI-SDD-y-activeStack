import { calcularCambios, camposVacios } from "./formulario";

describe("camposVacios", () => {
  it("marca el obligatorio vacío", () => {
    expect(
      camposVacios({ nombre: "Ana", apellido: "" }, ["nombre", "apellido"]),
    ).toEqual(["apellido"]);
  });

  it("marca el obligatorio formado solo por espacios", () => {
    expect(camposVacios({ nombre: "   " }, ["nombre"])).toEqual(["nombre"]);
  });

  it("ignora un opcional vacío", () => {
    expect(camposVacios({ nombre: "Ana", matricula: "" }, ["nombre"])).toEqual(
      [],
    );
  });

  it("devuelve todos los vacíos en el orden de los obligatorios", () => {
    expect(camposVacios({ a: "", b: "x", c: " " }, ["c", "b", "a"])).toEqual([
      "c",
      "a",
    ]);
  });
});

describe("calcularCambios", () => {
  const actual = { nombre: "Ana", apellido: "Ficticia", matricula: "MN-0001" };

  it("devuelve solo el campo cambiado", () => {
    expect(
      calcularCambios(actual, { ...actual, apellido: "Ficticia Segunda" }, [
        "matricula",
      ]),
    ).toEqual({ apellido: "Ficticia Segunda" });
  });

  it("no cuenta los espacios al final como un cambio", () => {
    expect(
      calcularCambios(actual, { ...actual, nombre: "Ana " }, ["matricula"]),
    ).toEqual({});
  });

  it("envía el valor recortado cuando cambia", () => {
    expect(
      calcularCambios(actual, { ...actual, nombre: "  Beatriz " }, []),
    ).toEqual({ nombre: "Beatriz" });
  });

  it("un opcional vaciado vale null", () => {
    expect(
      calcularCambios(actual, { ...actual, matricula: "" }, ["matricula"]),
    ).toEqual({ matricula: null });
  });

  it("un opcional que ya era nulo y sigue vacío no cambia", () => {
    expect(
      calcularCambios(
        { nombre: "Ana", matricula: null },
        { nombre: "Ana", matricula: "  " },
        ["matricula"],
      ),
    ).toEqual({});
  });

  it("un opcional nulo que se completa se envía", () => {
    expect(
      calcularCambios(
        { nombre: "Ana", matricula: null },
        { nombre: "Ana", matricula: "MN-0002" },
        ["matricula"],
      ),
    ).toEqual({ matricula: "MN-0002" });
  });

  it("compara los números como números", () => {
    expect(
      calcularCambios({ duracion_min: 30 }, { duracion_min: 30 }, []),
    ).toEqual({});
    expect(
      calcularCambios({ duracion_min: 30 }, { duracion_min: 45 }, []),
    ).toEqual({ duracion_min: 45 });
  });

  it("compara los booleanos", () => {
    expect(
      calcularCambios(
        { requiere_sillon: false },
        { requiere_sillon: true },
        [],
      ),
    ).toEqual({ requiere_sillon: true });
    expect(
      calcularCambios({ requiere_sillon: true }, { requiere_sillon: true }, []),
    ).toEqual({});
  });

  it("compara las horas HH:MM:SS de la API contra HH:MM del formulario", () => {
    expect(
      calcularCambios(
        { hora_inicio: "09:00:00", hora_fin: "13:00:00" },
        { hora_inicio: "09:00", hora_fin: "12:00" },
        [],
      ),
    ).toEqual({ hora_fin: "12:00" });
  });
});
