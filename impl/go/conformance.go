package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type vectorFile struct {
	SpecVersion string            `json:"spec_version"`
	Cases       []json.RawMessage `json:"cases"`
}

type kase struct {
	Name           string                   `json:"name"`
	Kind           string                   `json:"kind"`
	Body           map[string]interface{}   `json:"body"`
	Prev           string                   `json:"prev"`
	Canonical      string                   `json:"canonical"`
	Seal           string                   `json:"seal"`
	Receipts       []map[string]interface{} `json:"receipts"`
	Verdict        string                   `json:"verdict"`
	FailAt         int                      `json:"fail_at"`
	OffendingField string                   `json:"offending_field"`
}

func decode(b []byte, v interface{}) error {
	d := json.NewDecoder(bytes.NewReader(b))
	d.UseNumber() // never let Go re-format a number from the vectors
	return d.Decode(v)
}

func main() {
	root, _ := filepath.Abs(filepath.Join("..", ".."))
	path := filepath.Join(root, "tests", "vectors.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		fmt.Println("cannot read", path, "-", err)
		os.Exit(1)
	}
	var vf vectorFile
	if err := decode(raw, &vf); err != nil {
		fmt.Println("cannot parse vectors:", err)
		os.Exit(1)
	}

	fmt.Printf("KYA Receipt Chain %s - Go conformance\n", vf.SpecVersion)
	var fails []string
	check := func(ok bool, name, kind, detail string) {
		status := "PASS"
		if !ok {
			status = "FAIL"
			fails = append(fails, name+": "+detail)
		}
		fmt.Printf("  %s %-34s %s\n", status, name, kind)
	}

	for _, rawCase := range vf.Cases {
		var c kase
		if err := decode(rawCase, &c); err != nil {
			check(false, "?", "?", "undecodable case: "+err.Error())
			continue
		}
		switch c.Kind {
		case "canonical":
			// Canonical form only. The body carries characters above 0x7E,
			// which SPEC.md section 5 rejects before sealing -- the case
			// exists so implementations agree on the escaping anyway, per
			// section 4. encoding/json would escape < > and & here as well,
			// which is why this package writes its own serialiser.
			got, err := Canonical(c.Body)
			if err != nil {
				check(false, c.Name, c.Kind, err.Error())
				continue
			}
			check(got == c.Canonical, c.Name, c.Kind,
				"canonical mismatch\n      want "+c.Canonical+"\n      got  "+got)
		case "seal":
			got, err := Canonical(c.Body)
			if err != nil {
				check(false, c.Name, c.Kind, err.Error())
				continue
			}
			if got != c.Canonical {
				check(false, c.Name, c.Kind,
					"canonical mismatch\n      want "+c.Canonical+"\n      got  "+got)
				continue
			}
			s, err := Seal(c.Body, c.Prev)
			if err != nil {
				check(false, c.Name, c.Kind, err.Error())
				continue
			}
			check(s == c.Seal, c.Name, c.Kind, "seal want "+c.Seal+" got "+s)
		case "chain":
			got, err := Verify(c.Receipts)
			if err != nil {
				check(false, c.Name, c.Kind, err.Error())
				continue
			}
			want := 0
			if c.Verdict != "PASS" {
				want = c.FailAt
			}
			check(got == want, c.Name, c.Kind,
				fmt.Sprintf("expected fail_at=%d, got %d", want, got))
		case "reject":
			field := NonASCIIField(c.Body)
			check(field == c.OffendingField, c.Name, c.Kind,
				"expected rejection naming "+c.OffendingField+", got "+field)
		default:
			check(false, c.Name, c.Kind, "unknown case kind")
		}
	}

	fmt.Println()
	if len(fails) > 0 {
		fmt.Printf("NOT CONFORMANT - %d failure(s):\n", len(fails))
		for _, f := range fails {
			fmt.Println("  -", strings.TrimSpace(f))
		}
		os.Exit(1)
	}
	fmt.Printf("CONFORMANT: %d/%d cases\n", len(vf.Cases), len(vf.Cases))
}
