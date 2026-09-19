import type { Structure, ViewSettings } from "@/types/heartai";
interface Props { structures: Structure[]; views: ViewSettings; selected: string; onSelect: (name: string) => void; onChange: (name: string, patch: Partial<ViewSettings[string]>) => void; onFocus: (name: string) => void }
export default function StructureControls({ structures, views, selected, onSelect, onChange, onFocus }: Props) {
  return <section className="anatomy-panel"><div className="panel-heading"><h3>Anatomy</h3><span>{structures.length} structures</span></div>
    <div className="structure-list">{structures.map(s => <div key={s.name} className={`structure ${selected === s.name ? "selected" : ""}`}>
      <div className="structure-row"><input type="checkbox" aria-label={`Show ${s.label}`} checked={views[s.name]?.visible ?? true} onChange={e => onChange(s.name, { visible: e.target.checked })} />
        <span className="color-dot" style={{ background: s.color }} /><button className="structure-name" onClick={() => onSelect(s.name)} aria-pressed={selected === s.name}>{s.label}</button>
        <button className="focus-button" title={`Focus ${s.label}`} aria-label={`Focus ${s.label}`} onClick={() => onFocus(s.name)}>⊙</button></div>
      {selected === s.name && <label className="opacity">Opacity <input type="range" min="0.1" max="1" step="0.05" value={views[s.name]?.opacity ?? 1} onChange={e => onChange(s.name, { opacity: Number(e.target.value) })} /><span>{Math.round((views[s.name]?.opacity ?? 1) * 100)}%</span></label>}
    </div>)}</div>
  </section>;
}
