"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useState } from "react";
import { Eye, Trash2, Calendar, BarChart2, Building2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Client {
  id: string;
  name: string;
  industry: string;
  createdAt: string;
  estimateCount: number;
  lastActivity: string;
  status: string;
  logo: string;
  color: string;
}

interface ClientCardProps {
  client: Client;
  onDelete: (id: string) => void;
}

export default function ClientCard({ client, onDelete }: ClientCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -3 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer group"
    >
      {/* Card header gradient */}
      <div className={`h-2 w-full bg-gradient-to-r ${client.color}`} />

      <div className="p-5">
        {/* Logo and name */}
        <div className="flex items-start gap-3 mb-4">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${client.color} shadow-lg`}>
            {client.logo}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-slate-900 text-base truncate group-hover:text-blue-600 transition-colors">
              {client.name}
            </h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Building2 className="w-3 h-3 text-slate-400" />
              <p className="text-slate-500 text-xs truncate">{client.industry}</p>
            </div>
          </div>
          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
            Active
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <BarChart2 className="w-3 h-3 text-blue-500" />
              <p className="text-xs text-slate-500">Estimates</p>
            </div>
            <p className="text-2xl font-bold text-slate-900">{client.estimateCount}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Calendar className="w-3 h-3 text-violet-500" />
              <p className="text-xs text-slate-500">Created</p>
            </div>
            <p className="text-xs font-semibold text-slate-700">{client.createdAt}</p>
          </div>
        </div>

        <p className="text-xs text-slate-400 mb-4">Last activity: {client.lastActivity}</p>

        {/* Actions */}
        <div className="flex gap-2">
          <Link href={`/clients/${client.id}/estimates`} className="flex-1">
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              className="w-full flex items-center justify-center gap-2 py-2 text-sm font-semibold text-white rounded-xl transition-all btn-shine"
              style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
            >
              <Eye className="w-4 h-4" />
              View Estimates
              <ArrowRight className="w-3 h-3" />
            </motion.button>
          </Link>

          {showDeleteConfirm ? (
            <div className="flex gap-1">
              <button
                onClick={() => onDelete(client.id)}
                className="px-3 py-2 text-xs font-semibold bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
              >
                Confirm
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3 py-2 text-xs font-semibold bg-slate-200 text-slate-600 rounded-xl hover:bg-slate-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowDeleteConfirm(true)}
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all border border-slate-200"
            >
              <Trash2 className="w-4 h-4" />
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
