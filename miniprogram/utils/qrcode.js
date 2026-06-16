/**
 * QR Code Generator for WeChat Mini Program
 * Supports: Byte mode, ECC Level M, Version 2-6
 * Usage: drawQRCode(ctx, text, x, y, moduleSize, color)
 */

// ─── GF(256) with primitive polynomial 0x11D ───
const GF_EXP = new Array(512)
const GF_LOG = new Array(256)
;(function () {
  let v = 1
  for (let i = 0; i < 255; i++) {
    GF_EXP[i] = v; GF_LOG[v] = i
    v = (v * 2) ^ (v >= 128 ? 0x11D : 0)
  }
  for (let i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255]
})()

function gfMul(a, b) {
  return (a === 0 || b === 0) ? 0 : GF_EXP[GF_LOG[a] + GF_LOG[b]]
}

// ─── Reed-Solomon ───
function rsGenPoly(eccCount) {
  let g = [1]
  for (let i = 0; i < eccCount; i++) {
    const a = GF_EXP[i], ng = new Array(g.length + 1).fill(0)
    for (let j = 0; j < g.length; j++) {
      ng[j] ^= gfMul(g[j], a); ng[j + 1] ^= g[j]
    }
    g = ng
  }
  return g
}

function rsEncode(data, eccCount) {
  const gen = rsGenPoly(eccCount), gl = gen.map(c => GF_LOG[c])
  const buf = data.slice().concat(new Array(eccCount).fill(0))
  for (let i = 0; i < data.length; i++) {
    if (buf[i] === 0) continue
    const f = GF_LOG[buf[i]]
    for (let j = 0; j < gen.length; j++) buf[i + j] ^= GF_EXP[(f + gl[j]) % 255]
  }
  return buf.slice(data.length)
}

// ─── Version table: [version, modules, dataCodewords, eccCodewords, byteCapacity] ───
const VERSIONS = [
  [2, 25, 16, 10, 22], [3, 29, 26, 14, 36],
  [4, 33, 36, 18, 50], [5, 37, 48, 22, 67],
  [6, 41, 64, 28, 89],
]

// ─── Alignment pattern positions ───
const ALIGN_POS = { 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34] }

// ─── UTF-8 encode ───
function utf8Encode(s) {
  const b = []
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i)
    if (c < 0x80) b.push(c)
    else if (c < 0x800) b.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F))
    else if (c < 0x10000) b.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F))
    else b.push(0xF0 | (c >> 18), 0x80 | ((c >> 12) & 0x3F), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F))
  }
  return b
}

// ─── Encode data into codewords ───
function encodeData(text, version) {
  const v = VERSIONS.find(x => x[0] === version)
  const dataBytes = utf8Encode(text)
  const dataCapBits = v[2] * 8

  const bits = []
  // Mode indicator: 0100 (byte)
  bits.push(0, 1, 0, 0)
  // Character count (8 bits for v1-9)
  const cnt = dataBytes.length
  for (let i = 7; i >= 0; i--) bits.push((cnt >> i) & 1)
  // Data bits
  for (const b of dataBytes)
    for (let i = 7; i >= 0; i--) bits.push((b >> i) & 1)
  // Terminator
  for (let i = 0; i < Math.min(4, dataCapBits - bits.length); i++) bits.push(0)
  // Pad to byte
  while (bits.length % 8) bits.push(0)
  // Pad to capacity
  const padBytes = [0xEC, 0x11]
  for (let pi = 0; bits.length < dataCapBits; pi++)
    for (let i = 7; i >= 0; i--) bits.push((padBytes[pi % 2] >> i) & 1)

  const cw = []
  for (let i = 0; i < bits.length; i += 8) {
    let byte = 0
    for (let j = 0; j < 8; j++) byte = (byte << 1) | bits[i + j]
    cw.push(byte)
  }
  return cw.slice(0, v[2])
}

// ─── Build QR code matrix ───
function buildMatrix(text) {
  // Select version
  const dataBytes = utf8Encode(text)
  const ver = VERSIONS.find(v => dataBytes.length <= v[4]) || VERSIONS[VERSIONS.length - 1]
  const [version, mods, , eccCount] = ver
  const size = mods

  // Encode
  const data = encodeData(text, version)
  const ecc = rsEncode(data, eccCount)
  const allData = data.concat(ecc)

  // Matrix with borders (add 4 modules quiet zone on each side)
  const mSize = size + 8
  const m = Array.from({ length: mSize }, () => new Array(mSize).fill(-1))

  function setModule(r, c, val) { m[r + 4][c + 4] = val }
  function setRegion(r1, c1, r2, c2, val) {
    for (let r = r1; r <= r2; r++)
      for (let c = c1; c <= c2; c++) setModule(r, c, val)
  }

  // Finder patterns (7×7) at (0,0), (0, size-7), (size-7, 0)
  function drawFinder(r, c) {
    for (let i = -1; i <= 7; i++) {
      for (let j = -1; j <= 7; j++) {
        if (r + i < 0 || r + i >= size || c + j < 0 || c + j >= size) continue
        if (i < 0 || i > 6 || j < 0 || j > 6) { setModule(r + i, c + j, 0); continue }
        const val = (i === 0 || i === 6 || j === 0 || j === 6) ? 1
          : (i === 1 || i === 5 || j === 1 || j === 5) ? 0
          : (i === 2 || i === 4 || j === 2 || j === 4) ? 1
          : 0
        setModule(r + i, c + j, val)
      }
    }
  }
  drawFinder(0, 0)
  drawFinder(0, size - 7)
  drawFinder(size - 7, 0)

  // Timing patterns (row 6, col 6)
  for (let i = 8; i < size - 8; i++) {
    setModule(6, i, i % 2 === 0 ? 1 : 0)
    setModule(i, 6, i % 2 === 0 ? 1 : 0)
  }

  // Alignment patterns
  const alignPos = ALIGN_POS[version]
  if (alignPos) {
    for (const ar of alignPos)
      for (const ac of alignPos) {
        if (ar < 7 && ac < 7) continue
        if (ar < 7 && ac >= size - 7) continue
        if (ar >= size - 7 && ac < 7) continue
        const r0 = ar - 2, c0 = ac - 2
        for (let r = 0; r < 5; r++)
          for (let c = 0; c < 5; c++) {
            if (r0 + r < 0 || r0 + r >= size || c0 + c < 0 || c0 + c >= size) continue
            const val = (r === 0 || r === 4 || c === 0 || c === 4) ? 1
              : (r === 1 || r === 3 || c === 1 || c === 3) ? 0
              : 1
            setModule(r0 + r, c0 + c, val)
          }
      }
  }

  // Reserve format info areas
  // Around top-left finder
  for (let i = 0; i <= 8; i++) {
    if (i <= 8) { setModule(8, i, -2); setModule(i, 8, -2) }
  }
  // Around top-right finder
  for (let i = size - 8; i < size; i++) setModule(8, i, -2)
  // Around bottom-left finder
  for (let i = size - 8; i < size; i++) setModule(i, 8, -2)
  // Dark module
  setModule(size - 8, 8, 1)

  // Place data bits
  let bitIdx = 0
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5
    for (let row = 0; row < size; row++) {
      for (const col of [right, right - 1]) {
        for (const r of [size - 1 - row, row]) {
          if (col < 0 || r < 0 || r >= size) continue
          if (m[r + 4][col + 4] !== -1 || m[r + 4][col + 4] === -2) continue
          if (bitIdx < allData.length * 8) {
            const byteIdx = bitIdx >> 3
            const bitPos = 7 - (bitIdx & 7)
            m[r + 4][col + 4] = (allData[byteIdx] >> bitPos) & 1
            bitIdx++
          }
        }
      }
    }
  }

  // Apply mask
  const fmtMask = m => {
    const penalty = []
    for (let mask = 0; mask < 8; mask++) {
      let score = 0
      for (let r = 0; r < mSize; r++)
        for (let c = 0; c < mSize; c++) {
          if (m[r][c] < 0) continue
          let val = m[r][c]
          const rr = r - 4, cc = c - 4
          if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue
          let masked
          switch (mask) {
            case 0: masked = val ^ ((rr + cc) % 2 === 0 ? 1 : 0); break
            case 1: masked = val ^ (rr % 2 === 0 ? 1 : 0); break
            case 2: masked = val ^ (cc % 3 === 0 ? 1 : 0); break
            case 3: masked = val ^ ((rr + cc) % 3 === 0 ? 1 : 0); break
            case 4: masked = val ^ ((Math.floor(rr / 2) + Math.floor(cc / 3)) % 2 === 0 ? 1 : 0); break
            case 5: masked = val ^ ((rr * cc) % 2 + (rr * cc) % 3 === 0 ? 1 : 0); break
            case 6: masked = val ^ (((rr * cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
            case 7: masked = val ^ (((rr + cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
          }
          m[r][c] = masked
        }

      // Penalty scoring (simplified)
      score = 0
      for (let r = 0; r < mSize; r++) {
        for (let c = 0; c < mSize - 4; c++) {
          const v = m[r][c]
          if (v >= 0 && m[r][c + 1] === v && m[r][c + 2] === v && m[r][c + 3] === v && m[r][c + 4] === v)
            score += 30
        }
      }
      for (let c = 0; c < mSize; c++) {
        for (let r = 0; r < mSize - 4; r++) {
          const v = m[r][c]
          if (v >= 0 && m[r + 1][c] === v && m[r + 2][c] === v && m[r + 3][c] === v && m[r + 4][c] === v)
            score += 30
        }
      }
      // 2x2 blocks
      for (let r = 0; r < mSize - 1; r++)
        for (let c = 0; c < mSize - 1; c++) {
          if (m[r][c] >= 0 && m[r][c] === m[r + 1][c] && m[r][c] === m[r][c + 1] && m[r][c] === m[r + 1][c + 1])
            score += 3
        }
      penalty.push(score)
      // Unmask for next iteration
      for (let r = 0; r < mSize; r++)
        for (let c = 0; c < mSize; c++) {
          if (m[r][c] < 0) continue
          const rr = r - 4, cc = c - 4
          if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue
          let masked
          switch (mask) {
            case 0: masked = m[r][c] ^ ((rr + cc) % 2 === 0 ? 1 : 0); break
            case 1: masked = m[r][c] ^ (rr % 2 === 0 ? 1 : 0); break
            case 2: masked = m[r][c] ^ (cc % 3 === 0 ? 1 : 0); break
            case 3: masked = m[r][c] ^ ((rr + cc) % 3 === 0 ? 1 : 0); break
            case 4: masked = m[r][c] ^ ((Math.floor(rr / 2) + Math.floor(cc / 3)) % 2 === 0 ? 1 : 0); break
            case 5: masked = m[r][c] ^ ((rr * cc) % 2 + (rr * cc) % 3 === 0 ? 1 : 0); break
            case 6: masked = m[r][c] ^ (((rr * cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
            case 7: masked = m[r][c] ^ (((rr + cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
          }
          m[r][c] = masked
        }
    }

    // Select best mask
    const bestMask = penalty.indexOf(Math.min(...penalty))
    // Apply best mask permanently
    for (let r = 0; r < mSize; r++)
      for (let c = 0; c < mSize; c++) {
        if (m[r][c] < 0) continue
        const rr = r - 4, cc = c - 4
        if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue
        let val = m[r][c]
        let masked
        switch (bestMask) {
          case 0: masked = val ^ ((rr + cc) % 2 === 0 ? 1 : 0); break
          case 1: masked = val ^ (rr % 2 === 0 ? 1 : 0); break
          case 2: masked = val ^ (cc % 3 === 0 ? 1 : 0); break
          case 3: masked = val ^ ((rr + cc) % 3 === 0 ? 1 : 0); break
          case 4: masked = val ^ ((Math.floor(rr / 2) + Math.floor(cc / 3)) % 2 === 0 ? 1 : 0); break
          case 5: masked = val ^ ((rr * cc) % 2 + (rr * cc) % 3 === 0 ? 1 : 0); break
          case 6: masked = val ^ (((rr * cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
          case 7: masked = val ^ (((rr + cc) % 2 + (rr * cc) % 3) % 2 === 0 ? 1 : 0); break
        }
        m[r][c] = masked
      }
    return bestMask
  }

  const bestMask = fmtMask(m)

  // Format info bits
  const fmtECCMap = { 2: 0, 4: 1, 6: 3, 8: 2 } // error correction L=1, M=0, Q=3, H=2
  const eccBits = 0 // M = 00
  const fmtData = (eccBits << 3) | bestMask
  const fmtBCH = fmtData
  // BCH encoding: multiply by x^10, divide by generator 10100110111 (0x537)
  let bch = fmtBCH << 10
  const genPolyBCH = 0x537
  for (let i = 14; i >= 10; i--) {
    if ((bch >> i) & 1) bch ^= genPolyBCH << (i - 10)
  }
  const fmtBits = ((fmtBCH << 10) | bch) ^ 0x5412
  // Place format bits (two copies, LSB first)
  // Copy 1: around top-left finder
  const fmtPos1 = [
    [0, 8], [1, 8], [2, 8], [3, 8], [4, 8], [5, 8],
    [7, 8], [8, 8], [8, 7], [8, 5], [8, 4], [8, 3], [8, 2], [8, 1], [8, 0]
  ]
  // Copy 2: around top-right (row 8, cols size-1..size-7) and bottom-left (col 8, rows size-8..size-1)
  const fmtPos2 = []
  for (let i = 0; i < 7; i++) fmtPos2.push([8, size - 1 - i])
  for (let i = 0; i < 8; i++) fmtPos2.push([size - 8 + i, 8])
  for (let i = 0; i < 15; i++) {
    const bit = (fmtBits >> i) & 1  // LSB = bit 0
    setModule(fmtPos1[i][0], fmtPos1[i][1], bit)
    setModule(fmtPos2[i][0], fmtPos2[i][1], bit)
  }

  // Clear reserved (-2) cells
  for (let r = 0; r < mSize; r++)
    for (let c = 0; c < mSize; c++)
      if (m[r][c] === -2) m[r][c] = -1

  return { matrix: m, moduleCount: mSize }
}

// ─── Draw QR code on canvas context ───
function drawQRCode(ctx, text, x, y, moduleSize, color) {
  const { matrix, moduleCount } = buildMatrix(text)
  const totalSize = moduleCount * moduleSize
  const black = color || '#1a1a1a'

  // Fill white background
  ctx.fillStyle = '#FFFFFF'
  ctx.fillRect(x, y, totalSize, totalSize)

  // Draw modules
  ctx.fillStyle = black
  for (let r = 0; r < moduleCount; r++) {
    for (let c = 0; c < moduleCount; c++) {
      if (matrix[r][c] === 1) {
        ctx.fillRect(x + c * moduleSize, y + r * moduleSize, moduleSize, moduleSize)
      }
    }
  }

  return totalSize
}

module.exports = { drawQRCode }
