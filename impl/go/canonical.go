// Package main is a third implementation of the KYA Receipt Chain, written
// from SPEC.md alone rather than by translating the Python or JavaScript.
//
// That is the point of it. Two implementations that agree may agree because
// one was copied from the other; a third, written from the prose, tests
// whether the prose is actually sufficient. Where this disagreed with the
// vectors, the specification was ambiguous and got fixed.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

// canonicalString renders a JSON string per SPEC.md section 4: ASCII only,
// with everything outside 0x20-0x7E escaped.
//
// SPEC.md section 4 states the ASCII rule and the separators, but does not
// enumerate the escapes JSON itself requires for quote, backslash and the
// control characters. Those are taken from RFC 8259, which is the only
// reading that can round-trip. Noted as a specification gap; see the report.
func canonicalString(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case '\b':
			b.WriteString(`\b`)
		case '\f':
			b.WriteString(`\f`)
		default:
			switch {
			case r < 0x20 || r > 0x7E:
				// Non-ASCII and control characters as \uXXXX, lowercase hex.
				// Runes above the BMP become a surrogate pair, as JSON requires.
				if r > 0xFFFF {
					r -= 0x10000
					hi := 0xD800 + (r >> 10)
					lo := 0xDC00 + (r & 0x3FF)
					fmt.Fprintf(&b, `\u%04x\u%04x`, hi, lo)
				} else {
					fmt.Fprintf(&b, `\u%04x`, r)
				}
			default:
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
	return b.String()
}

// Canonical implements SPEC.md section 4: keys sorted by code point at every
// level, "," and ":" separators, no whitespace, ASCII only, no trailing newline.
func Canonical(v interface{}) (string, error) {
	switch t := v.(type) {
	case nil:
		return "null", nil
	case bool:
		if t {
			return "true", nil
		}
		return "false", nil
	case string:
		return canonicalString(t), nil
	case json.Number:
		// Preserved verbatim from the input. Re-formatting a number is how
		// two implementations silently stop agreeing; SPEC.md section 4
		// carries amounts as strings for exactly this reason.
		return t.String(), nil
	case []interface{}:
		parts := make([]string, len(t))
		for i, e := range t {
			s, err := Canonical(e)
			if err != nil {
				return "", err
			}
			parts[i] = s
		}
		return "[" + strings.Join(parts, ",") + "]", nil
	case map[string]interface{}:
		keys := make([]string, 0, len(t))
		for k := range t {
			keys = append(keys, k)
		}
		sort.Strings(keys) // Go compares strings bytewise: code point order
		parts := make([]string, len(keys))
		for i, k := range keys {
			s, err := Canonical(t[k])
			if err != nil {
				return "", err
			}
			parts[i] = canonicalString(k) + ":" + s
		}
		return "{" + strings.Join(parts, ",") + "}", nil
	default:
		return "", fmt.Errorf("cannot canonicalise %T", v)
	}
}

// Seal implements SPEC.md section 3: sha256(canonical(body) + prev), lowercase hex.
func Seal(body map[string]interface{}, prev string) (string, error) {
	c, err := Canonical(body)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(c + prev))
	return hex.EncodeToString(sum[:]), nil
}

// NonASCIIField implements SPEC.md section 5. Returns the name of the first
// field carrying a character outside ASCII, or "" if the body is clean. A
// conforming implementation must refuse to seal such a receipt.
func NonASCIIField(body map[string]interface{}) string {
	keys := make([]string, 0, len(body))
	for k := range body {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		if !isASCII(k) {
			return k
		}
		if s, ok := body[k].(string); ok && !isASCII(s) {
			return k
		}
	}
	return ""
}

func isASCII(s string) bool {
	for _, r := range s {
		if r > 0x7F {
			return false
		}
	}
	return true
}

// Verify implements SPEC.md section 7. Returns 0 if the chain holds, or the
// 1-based position of the FIRST receipt that fails.
func Verify(receipts []map[string]interface{}) (int, error) {
	prev := "GENESIS"
	for _, r := range receipts {
		n, err := position(r)
		if err != nil {
			return 0, err
		}
		gotPrev, _ := r["prev"].(string)
		if gotPrev != prev {
			return n, nil
		}
		body := make(map[string]interface{}, len(r))
		for k, v := range r {
			if k != "seal" {
				body[k] = v
			}
		}
		want, _ := r["seal"].(string)
		got, err := Seal(body, prev)
		if err != nil {
			return 0, err
		}
		if got != want {
			return n, nil
		}
		prev = want
	}
	return 0, nil
}

func position(r map[string]interface{}) (int, error) {
	num, ok := r["n"].(json.Number)
	if !ok {
		return 0, fmt.Errorf("receipt has no numeric n")
	}
	i, err := num.Int64()
	return int(i), err
}
