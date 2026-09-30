"""Decodifica o formato de linha compacta retornado por Routes API."""

from src.core.travel.models import Coordinate


def midpoint(encoded: str | None) -> Coordinate | None:
    if not encoded:
        return None
    coordinates: list[Coordinate] = []
    index = latitude = longitude = 0
    try:
        while index < len(encoded):
            deltas = []
            for _ in range(2):
                shift = value = 0
                while True:
                    chunk = ord(encoded[index]) - 63
                    index += 1
                    value |= (chunk & 0x1F) << shift
                    shift += 5
                    if chunk < 0x20:
                        break
                deltas.append(~(value >> 1) if value & 1 else value >> 1)
            latitude += deltas[0]
            longitude += deltas[1]
            coordinates.append(
                Coordinate(latitude=latitude / 100000, longitude=longitude / 100000)
            )
    except (IndexError, ValueError):
        return None
    return coordinates[len(coordinates) // 2] if coordinates else None
