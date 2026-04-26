"use client";

import { FileVideo, Image as ImageIcon, Music, FileText } from "lucide-react";

interface AssetPreviewProps {
  asset: {
    id: number;
    asset_type: string;
    file_path: string;
    mime_type?: string;
  };
  showControls?: boolean;
}

const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api-proxy";

export default function AssetPreview({ asset, showControls = true }: AssetPreviewProps) {
  const fileUrl = `${BASE}/api/outputs/${asset.id}/file`;
  const mime = asset.mime_type || "";

  if (mime.startsWith("image/") || asset.asset_type === "image") {
    return (
      <img
        src={fileUrl}
        alt={asset.asset_type}
        className="rounded-lg w-full object-cover"
      />
    );
  }

  if (mime.startsWith("video/") || asset.asset_type === "video") {
    return (
      <video
        src={fileUrl}
        controls={showControls}
        className="rounded-lg w-full"
        style={{ maxHeight: 400 }}
      />
    );
  }

  if (mime.startsWith("audio/") || asset.asset_type === "audio") {
    return (
      <div className="flex flex-col items-center gap-2 py-4">
        <Music className="h-10 w-10 text-purple-400" />
        {showControls && <audio src={fileUrl} controls className="w-full mt-2" />}
      </div>
    );
  }

  // Script or other
  const Icon = asset.asset_type === "video" ? FileVideo
    : asset.asset_type === "image" ? ImageIcon
    : FileText;

  return (
    <div className="flex flex-col items-center gap-2 py-6 text-gray-400">
      <Icon className="h-10 w-10" />
      <p className="text-xs">{asset.asset_type}</p>
      <a
        href={fileUrl}
        download
        className="text-xs text-blue-500 underline"
      >
        Descargar
      </a>
    </div>
  );
}
