"""Grafo de información y correlación entre hallazgos.

Modela la investigación como un grafo: en el centro, el sujeto; alrededor, las
entidades encontradas (emails, teléfonos, perfiles, páginas, ubicaciones). Cada
arista recuerda de qué fuente salió. Una entidad que aparece a través de VARIAS
fuentes distintas es una correlación: la señal más valiosa de una investigación
OSINT, porque está corroborada.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

# Colores por tipo de nodo (para el PNG).
_COLORES = {
    "sujeto": "#ef4444",
    "email": "#3b82f6",
    "telefono": "#22c55e",
    "perfil": "#a855f7",
    "pagina": "#64748b",
    "ubicacion": "#f59e0b",
    "aviso": "#e11d48",
    "otro": "#94a3b8",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


@dataclass
class _Nodo:
    id: str
    tipo: str
    etiqueta: str
    fuentes: Set[str] = field(default_factory=set)


class Grafo:
    def __init__(self):
        self._nodos: Dict[str, _Nodo] = {}
        self._aristas: Dict[Tuple[str, str], Set[str]] = {}
        self._sujeto_id: str | None = None

    # ------------------------------------------------------------------ API
    def sujeto(self, etiqueta: str) -> str:
        nid = f"sujeto:{_norm(etiqueta)}"
        self._nodos.setdefault(nid, _Nodo(nid, "sujeto", etiqueta))
        self._sujeto_id = nid
        return nid

    def entidad(self, tipo: str, etiqueta: str, fuente: str) -> str:
        tipo = tipo if tipo in _COLORES else "otro"
        nid = f"{tipo}:{_norm(etiqueta)}"
        nodo = self._nodos.get(nid)
        if nodo is None:
            nodo = _Nodo(nid, tipo, etiqueta)
            self._nodos[nid] = nodo
        nodo.fuentes.add(fuente)
        # Conectar automáticamente con el sujeto si existe.
        if self._sujeto_id and nid != self._sujeto_id:
            self.relacion(self._sujeto_id, nid, fuente)
        return nid

    def relacion(self, a: str, b: str, fuente: str) -> None:
        if a == b:
            return
        clave = tuple(sorted((a, b)))
        self._aristas.setdefault(clave, set()).add(fuente)

    # ------------------------------------------------------- consultas
    def correlaciones(self) -> List[dict]:
        """Entidades corroboradas por 2+ fuentes distintas, de mayor a menor."""
        out = []
        for nid, nodo in self._nodos.items():
            if nodo.tipo == "sujeto":
                continue
            if len(nodo.fuentes) >= 2:
                out.append({"tipo": nodo.tipo, "valor": nodo.etiqueta,
                            "fuentes": sorted(nodo.fuentes), "n": len(nodo.fuentes)})
        out.sort(key=lambda d: d["n"], reverse=True)
        return out

    def resumen(self) -> dict:
        tipos: Dict[str, int] = {}
        for n in self._nodos.values():
            if n.tipo == "sujeto":
                continue
            tipos[n.tipo] = tipos.get(n.tipo, 0) + 1
        return {"nodos": len(self._nodos), "aristas": len(self._aristas), "por_tipo": tipos}

    # ----------------------------------------------------------- render
    def render_png(self, ruta: str) -> str | None:
        """Dibuja el grafo en un PNG. Devuelve la ruta o None si falta la librería."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import networkx as nx
        except Exception:
            return None
        if not self._nodos:
            return None

        G = nx.Graph()
        for nid, nodo in self._nodos.items():
            G.add_node(nid, tipo=nodo.tipo)
        for (a, b), fuentes in self._aristas.items():
            G.add_edge(a, b, weight=len(fuentes))

        pos = nx.spring_layout(G, k=0.9, seed=42)
        colores = [_COLORES.get(self._nodos[n].tipo, "#94a3b8") for n in G.nodes()]
        tam = [1400 if self._nodos[n].tipo == "sujeto" else 650 for n in G.nodes()]
        # Aristas corroboradas (2+ fuentes) más gruesas.
        anchos = [1.0 + 1.6 * (G[u][v]["weight"] - 1) for u, v in G.edges()]

        etiquetas = {}
        for nid, nodo in self._nodos.items():
            txt = nodo.etiqueta
            etiquetas[nid] = txt if len(txt) <= 26 else txt[:24] + "…"

        plt.figure(figsize=(12, 8))
        nx.draw_networkx_edges(G, pos, width=anchos, edge_color="#cbd5e1")
        nx.draw_networkx_nodes(G, pos, node_color=colores, node_size=tam,
                               edgecolors="#334155", linewidths=0.6)
        nx.draw_networkx_labels(G, pos, etiquetas, font_size=8)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(ruta, dpi=140, bbox_inches="tight")
        plt.close()
        return ruta
