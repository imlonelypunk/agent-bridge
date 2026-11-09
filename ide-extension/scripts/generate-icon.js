const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const size = 128;
const scale = 3;
const width = size * scale;
const pixels = Buffer.alloc(width * width * 4);

function color(hex) {
  return [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16)).concat(255);
}

function blendPixel(x, y, rgba) {
  if (x < 0 || y < 0 || x >= width || y >= width) return;
  const index = (y * width + x) * 4;
  pixels.set(rgba, index);
}

function paint(predicate, rgba) {
  for (let y = 0; y < width; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (predicate(x / scale, y / scale)) blendPixel(x, y, rgba);
    }
  }
}

function roundedSquare(x, y, extent, radius) {
  const cx = Math.max(radius, Math.min(extent - radius, x));
  const cy = Math.max(radius, Math.min(extent - radius, y));
  return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2;
}

function segmentDistance(x, y, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const length = dx * dx + dy * dy;
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / length));
  return Math.hypot(x - (ax + t * dx), y - (ay + t * dy));
}

function circle(x, y, cx, cy, radius, stroke, inset = false) {
  const distance = Math.hypot(x - cx, y - cy);
  return inset ? distance >= radius - stroke && distance <= radius : distance <= radius;
}

paint((x, y) => roundedSquare(x - 5, y - 5, 118, 25), color("171C2E"));

const bridgeColor = color("70D9D1");
paint((x, y) => segmentDistance(x, y, 35, 47, 93, 47) <= 3.5
  || segmentDistance(x, y, 35, 47, 64, 88) <= 3.5
  || segmentDistance(x, y, 93, 47, 64, 88) <= 3.5, bridgeColor);

paint((x, y) => circle(x, y, 35, 47, 16, 5, true), color("F4F5FA"));
paint((x, y) => circle(x, y, 93, 47, 16, 5, true), color("A99BFF"));
paint((x, y) => circle(x, y, 64, 89, 16, 5, true), color("F4F5FA"));
paint((x, y) => circle(x, y, 35, 47, 4), color("F4F5FA"));
paint((x, y) => circle(x, y, 93, 47, 4), color("A99BFF"));
paint((x, y) => circle(x, y, 64, 89, 4), color("F4F5FA"));

const reduced = Buffer.alloc(size * size * 4);
for (let y = 0; y < size; y += 1) {
  for (let x = 0; x < size; x += 1) {
    const output = (y * size + x) * 4;
    for (let channel = 0; channel < 4; channel += 1) {
      let sum = 0;
      for (let sy = 0; sy < scale; sy += 1) {
        for (let sx = 0; sx < scale; sx += 1) {
          sum += pixels[(((y * scale + sy) * width) + (x * scale + sx)) * 4 + channel];
        }
      }
      reduced[output + channel] = Math.round(sum / (scale * scale));
    }
  }
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(name, data) {
  const type = Buffer.from(name, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([type, data])));
  return Buffer.concat([length, type, data, checksum]);
}

const header = Buffer.alloc(13);
header.writeUInt32BE(size, 0);
header.writeUInt32BE(size, 4);
header[8] = 8;
header[9] = 6;
const rows = Buffer.alloc(size * (size * 4 + 1));
for (let y = 0; y < size; y += 1) {
  reduced.copy(rows, y * (size * 4 + 1) + 1, y * size * 4, (y + 1) * size * 4);
}
const png = Buffer.concat([
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  chunk("IHDR", header),
  chunk("IDAT", zlib.deflateSync(rows)),
  chunk("IEND", Buffer.alloc(0)),
]);
fs.writeFileSync(path.join(__dirname, "..", "icon.png"), png);
console.log("Generated the 128×128 Agent Bridge marketplace icon.");
