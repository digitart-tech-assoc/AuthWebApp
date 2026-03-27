"use client"

import { useState, useCallback, useEffect } from "react"
import {
  getPreMemberList,
  registerPaidInvitation,
  PreMember,
} from "@/actions/members"

export default function MembersPage() {
  const [members, setMembers] = useState<PreMember[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedMember, setSelectedMember] = useState<PreMember | null>(null)
  const [noteInput, setNoteInput] = useState("")
  const [actionLoading, setActionLoading] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Fetch pre-member list
  const loadMembers = useCallback(async (query?: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getPreMemberList(query || undefined)
      setMembers(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members")
    } finally {
      setLoading(false)
    }
  }, [])

  // Load members on mount
  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  // Handle search
  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    loadMembers(searchQuery)
  }

  // Register paid invitation
  const handleRegisterPaid = async (member: PreMember) => {
    setActionLoading(true)
    setError(null)
    try {
      const result = await registerPaidInvitation(member.discord_id, noteInput)
      if (result.ok) {
        setSuccessMessage("入会費清算を完了しました")
        setTimeout(() => {
          setSelectedMember(null)
          setNoteInput("")
          setSuccessMessage(null)
        }, 1000)
      } else {
        setError("Failed to register paid invitation")
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to register paid invitation"
      )
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">メンバー管理</h1>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          placeholder="Discord ID で検索"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "検索中..." : "検索"}
        </button>
        <button
          type="button"
          onClick={() => {
            setSearchQuery("")
            loadMembers()
          }}
          className="px-6 py-2 bg-gray-400 text-white rounded-lg hover:bg-gray-500"
        >
          クリア
        </button>
      </form>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Members list */}
      <div className="space-y-3">
        {members.length > 0 ? (
          members.map((member) => (
            <div
              key={member.discord_id}
              className={`flex items-center justify-between p-4 border rounded-lg ${
                member.is_paid
                  ? "bg-gray-100 opacity-50 cursor-not-allowed"
                  : "hover:bg-gray-50"
              }`}
            >
              <div>
                {member.discord_username && (
                  <div className="font-semibold text-lg">
                    {member.discord_username}
                    {member.discord_display_name &&
                      member.discord_display_name !== member.discord_username && (
                        <span className="text-sm text-gray-600 ml-2">
                          ({member.discord_display_name})
                        </span>
                      )}
                  </div>
                )}
                <div className="text-sm text-gray-600">
                  Discord ID: {member.discord_id}
                </div>
                {member.supabase_user_id && (
                  <div className="text-sm text-gray-600">
                    Supabase ID: {member.supabase_user_id}
                  </div>
                )}
                {member.user_id && (
                  <div className="text-sm text-gray-600">User ID: {member.user_id}</div>
                )}
                {member.assigned_at && (
                  <div className="text-xs text-gray-500">
                    登録日: {new Date(member.assigned_at).toLocaleString("ja-JP")}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedMember(member)}
                  disabled={member.is_paid}
                  className={`px-4 py-2 rounded ${
                    member.is_paid
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-blue-500 text-white hover:bg-blue-600"
                  }`}
                >
                  {member.is_paid ? "支払済み" : "詳細"}
                </button>
              </div>
            </div>
          ))
        ) : (
          <p className="text-gray-500">
            {loading ? "読み込み中..." : "Pre-member がいません"}
          </p>
        )}
      </div>

      {/* Modal for member actions */}
      {selectedMember && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6 space-y-4">
            {successMessage && (
              <div className="p-3 bg-green-100 border border-green-400 text-green-700 rounded">
                {successMessage}
              </div>
            )}
            <h2 className="text-2xl font-bold">
              {selectedMember.discord_username && (
                <div className="mb-2">
                  {selectedMember.discord_username}
                  {selectedMember.discord_display_name &&
                    selectedMember.discord_display_name !== selectedMember.discord_username && (
                      <div className="text-sm text-gray-600">
                        ({selectedMember.discord_display_name})
                      </div>
                    )}
                </div>
              )}
              <div className="text-base font-normal text-gray-600">
                Discord ID: {selectedMember.discord_id}
              </div>
            </h2>

            <div>
              <label className="block text-sm font-medium mb-2">
                メモ（オプション）
              </label>
              <textarea
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                placeholder="入会費支払い方法など"
                className="w-full px-3 py-2 border rounded-lg"
                rows={3}
              />
            </div>

            <button
              onClick={() => handleRegisterPaid(selectedMember)}
              disabled={actionLoading}
              className="w-full px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              {actionLoading ? "処理中..." : "入会費清算"}
            </button>

            <button
              onClick={() => {
                setSelectedMember(null)
                setNoteInput("")
              }}
              className="w-full px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
            >
              キャンセル
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
