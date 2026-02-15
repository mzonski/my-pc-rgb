# my-pc-rgb

A unified RGB controller for my PC.

## Background

This project addresses the limitations of OpenRGB with certain hardware:

- **ASUS Aura RGB Gen 2** devices (like the ASUS ROG Ryujin III EXTREME ARGB) are not supported by OpenRGB

## Supported Hardware

Currently integrated:
- ASUS ROG Ryujin III EXTREME ARGB
- ENE DDR5
- Corsair Lighting Node Core

**Planned:**
- ASUS GeForce RTX 5090 ROG Astral OC

## Features

- **Toggle Control** - Turn RGB devices on/off
- **Set device static color** - Set static color for all devices in sync
- **Set direct color** - Partially implemented
- **Unified Interface** - Control all components from one application

## Roadmap

1. ✅ ASUS Gen 2 RGB support
2. ✅ ENE DDR5 integration
3. ✅ Corsair Lighting Node Core integration
4. ✅ GPU support
5. ⏳ Solve ASUS Aura Gen 2 protocol completely
6. 📋 Contribute improvements back to OpenRGB

## Future Plans

Once all personal hardware is fully supported, the goal is to contribute this functionality to the OpenRGB project for broader community benefit.

## Acknowledgements

- [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB)
- [CorsairLightingProtocol](https://github.com/Legion2/CorsairLightingProtocol/)
- [Aura Addressable Header Controller](https://gitlab.com/cneil02/aura-addressable-header-controller)

---

*Note: This is a personal project developed to solve specific hardware compatibility issues.*
