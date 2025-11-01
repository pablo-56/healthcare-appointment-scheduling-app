import { useEffect, useState } from "react";

export default function Docs() {
    const [items, setItems] = useState<any[]>([]);
    useEffect(() => {
        (async () => {
            const r = await fetch("/api/v1/documents");
            const data = await r.json();
            setItems(data.items || []);
        })();
    }, []);
    return (
        <div className="p-6">
            <h1 className="text-xl mb-4">Documents</h1>
            <ul className="space-y-2">
                {items.map((d) => (
                    <li key={d.id} className="border p-2">
                        <div><b>{d.kind}</b> — #{d.id}</div>
                        <div>URL: {d.url}</div>
                        <div>Meta.sha256: {d.meta?.sha256}</div>
                        <div>Created: {d.created_at}</div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
