// Test de control: si la zona forzada de la suite no se aplicara, ningún test de horarios
// detectaría un uso accidental de la zona local de la máquina (D15).
describe("zona de la suite", () => {
  it("la zona efectiva es Asia/Tokyo", () => {
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe("Asia/Tokyo");
  });

  it("las 22:30 de Buenos Aires son las 10:30 del día siguiente en la zona local", () => {
    const instante = new Date("2026-11-09T22:30:00-03:00");

    expect(instante.getHours()).toBe(10);
    expect(instante.getDate()).toBe(10);
  });
});
