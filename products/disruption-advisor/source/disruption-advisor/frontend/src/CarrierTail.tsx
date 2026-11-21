/** Airline tail mark shown before a flight number (decorative: the flight number next to it carries the meaning). */
const TAILS = new Set(["G9", "3L", "3O", "4P", "9P", "E5"]);

export function carrierOf(flightNumber: string): string {
  return flightNumber.slice(0, 2).toUpperCase();
}

export function CarrierTail({ flightNumber }: { flightNumber: string }) {
  const carrier = carrierOf(flightNumber);
  if (!TAILS.has(carrier)) return null;
  return <img className="carrier-tail" src={`/brand/tails/${carrier}.svg`} alt="" width={20} height={15} />;
}
