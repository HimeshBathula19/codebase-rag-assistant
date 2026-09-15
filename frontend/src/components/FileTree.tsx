import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";
import { useState } from "react";
import type { FileNode } from "../types";

export function FileTree({
  nodes,
  selected,
  onSelect,
}: {
  nodes: FileNode[];
  selected?: string;
  onSelect: (node: FileNode) => void;
}) {
  return (
    <ul className="space-y-0.5 text-sm">
      {nodes.map((node) => (
        <TreeNode key={node.path} node={node} selected={selected} onSelect={onSelect} />
      ))}
    </ul>
  );
}

function TreeNode({
  node,
  selected,
  onSelect,
}: {
  node: FileNode;
  selected?: string;
  onSelect: (node: FileNode) => void;
}) {
  const [open, setOpen] = useState(node.type === "directory" && node.path.split("/").length < 2);
  if (node.type === "directory") {
    return (
      <li>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center gap-1 rounded px-1 py-0.5 text-left text-slate-700 hover:bg-slate-100"
        >
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          <Folder className="h-3.5 w-3.5 text-slate-400" />
          <span className="truncate">{node.name}</span>
        </button>
        {open && node.children ? (
          <div className="ml-3 border-l border-slate-200 pl-2">
            <FileTree nodes={node.children} selected={selected} onSelect={onSelect} />
          </div>
        ) : null}
      </li>
    );
  }
  const active = selected === node.path;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(node)}
        className={`flex w-full items-center gap-1 rounded px-1 py-0.5 text-left ${
          active ? "bg-accent-50 text-accent-700" : "text-slate-700 hover:bg-slate-100"
        }`}
      >
        <File className="ml-4 h-3.5 w-3.5 text-slate-400" />
        <span className="truncate">{node.name}</span>
      </button>
    </li>
  );
}
