/**
 * Global Users Management Page
 * SuperAdmin - Tüm kullanıcıları yönet
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { apiService } from '../services/api';

interface SuperUser {
  id: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  depot_id: string | null;
  depot_code: string | null;
  depot_name: string | null;
  station_id: string | null;
  station_name: string | null;
  created_at: string;
}

interface DepotOption {
  id: string;
  code: string;
  name: string;
}

export default function GlobalUsersPage({ navbarOverride }: { navbarOverride?: React.ReactNode }) {
  const [users, setUsers] = useState<SuperUser[]>([]);
  const [depots, setDepots] = useState<DepotOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [filterDepot, setFilterDepot] = useState('');

  // Yeni kullanıcı formu
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newRole, setNewRole] = useState('admin');
  const [newDepotId, setNewDepotId] = useState('');

  // Şifre sıfırlama
  const [resetUserId, setResetUserId] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState('');

  // Düzenleme
  const [editUser, setEditUser] = useState<SuperUser | null>(null);
  const [editFullName, setEditFullName] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editDepotId, setEditDepotId] = useState('');

  // Silme onay
  const [deleteUserId, setDeleteUserId] = useState<string | null>(null);
  const [deleteUsername, setDeleteUsername] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadUsers();
  }, [filterDepot]);

  const loadData = async () => {
    try {
      const depotsData = await apiService.getDepots();
      setDepots(depotsData.map((d) => ({ id: d.id, code: d.code, name: d.name })));
    } catch {
      // ignore
    }
  };

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await apiService.getSuperadminUsers(filterDepot || undefined);
      setUsers(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kullanıcılar yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiService.createSuperadminUser({
        username: newUsername,
        password: newPassword,
        full_name: newFullName || undefined,
        role: newRole,
        depot_id: newDepotId || undefined,
      });
      setShowCreateForm(false);
      setNewUsername('');
      setNewPassword('');
      setNewFullName('');
      setNewRole('admin');
      setNewDepotId('');
      setSuccess('Kullanıcı oluşturuldu');
      loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kullanıcı oluşturulamadı');
    }
  };

  const handleToggleActive = async (user: SuperUser) => {
    try {
      await apiService.updateSuperadminUser(user.id, { is_active: !user.is_active });
      loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'İşlem başarısız');
    }
  };

  const handleResetPassword = async () => {
    if (!resetUserId || !resetPassword) return;
    try {
      await apiService.updateSuperadminUser(resetUserId, { new_password: resetPassword });
      setResetUserId(null);
      setResetPassword('');
      setSuccess('Şifre sıfırlandı');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Şifre sıfırlanamadı');
    }
  };

  const openEditDialog = (user: SuperUser) => {
    setEditUser(user);
    setEditFullName(user.full_name || '');
    setEditRole(user.role);
    setEditDepotId(user.depot_id || '');
  };

  const handleEditUser = async () => {
    if (!editUser) return;
    try {
      await apiService.updateSuperadminUser(editUser.id, {
        full_name: editFullName || undefined,
        role: editRole,
        depot_id: editDepotId || undefined,
      });
      setEditUser(null);
      setSuccess('Kullanıcı güncellendi');
      loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Güncelleme başarısız');
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteUserId) return;
    try {
      await apiService.deactivateSuperadminUser(deleteUserId);
      setDeleteUserId(null);
      setDeleteUsername('');
      setSuccess('Kullanıcı silindi');
      loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Silme başarısız');
    }
  };

  const roleLabel = (role: string) => {
    switch (role) {
      case 'superadmin':
        return 'SuperAdmin';
      case 'admin':
        return 'Yönetici';
      case 'tablet':
        return 'Tablet';
      default:
        return role;
    }
  };

  const roleColor = (role: string) => {
    switch (role) {
      case 'superadmin':
        return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300';
      case 'admin':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
      case 'tablet':
        return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {navbarOverride || <Navbar />}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center space-x-4">
            <Link to={navbarOverride ? '/' : '/superadmin'} className="text-blue-600 dark:text-blue-400 hover:underline text-sm">
              SuperAdmin
            </Link>
            <span className="text-gray-400">/</span>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Kullanıcı Yönetimi</h1>
          </div>
          <div className="flex space-x-3">
            <select
              value={filterDepot}
              onChange={(e) => setFilterDepot(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
            >
              <option value="">Tüm Depolar</option>
              {depots.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
            >
              Yeni Kullanıcı
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-4">
            {error}
            <button onClick={() => setError(null)} className="float-right font-bold">x</button>
          </div>
        )}

        {success && (
          <div className="bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300 px-4 py-3 rounded mb-4">
            {success}
            <button onClick={() => setSuccess(null)} className="float-right font-bold">x</button>
          </div>
        )}

        {/* Yeni Kullanıcı Formu */}
        {showCreateForm && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Yeni Kullanıcı</h3>
            <form onSubmit={handleCreateUser} className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kullanıcı Adı</label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Şifre</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                  minLength={6}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ad Soyad</label>
                <input
                  type="text"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rol</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="admin">Yönetici</option>
                  <option value="tablet">Tablet</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Depo</label>
                <select
                  value={newDepotId}
                  onChange={(e) => setNewDepotId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  required
                >
                  <option value="">-- Depo Seçin --</option>
                  {depots.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end space-x-2">
                <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm">
                  Oluştur
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="bg-gray-400 text-white px-4 py-2 rounded-md hover:bg-gray-500 text-sm"
                >
                  İptal
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Şifre Sıfırlama Dialog */}
        {resetUserId && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Şifre Sıfırla</h3>
              <input
                type="password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                placeholder="Yeni şifre (min 6 karakter)"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 mb-4"
                minLength={6}
              />
              <div className="flex space-x-3">
                <button
                  onClick={handleResetPassword}
                  disabled={resetPassword.length < 6}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 text-sm"
                >
                  Sıfırla
                </button>
                <button
                  onClick={() => { setResetUserId(null); setResetPassword(''); }}
                  className="flex-1 bg-gray-400 text-white py-2 rounded-md hover:bg-gray-500 text-sm"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Düzenleme Dialog */}
        {editUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
                Kullanıcı Düzenle: <span className="font-mono text-blue-600 dark:text-blue-400">{editUser.username}</span>
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ad Soyad</label>
                  <input
                    type="text"
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rol</label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    <option value="admin">Yönetici</option>
                    <option value="tablet">Tablet</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Depo</label>
                  <select
                    value={editDepotId}
                    onChange={(e) => setEditDepotId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">-- Depo Seçin --</option>
                    {depots.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex space-x-3 mt-4">
                <button
                  onClick={handleEditUser}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 text-sm"
                >
                  Kaydet
                </button>
                <button
                  onClick={() => setEditUser(null)}
                  className="flex-1 bg-gray-400 text-white py-2 rounded-md hover:bg-gray-500 text-sm"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Silme Onay Dialog */}
        {deleteUserId && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Kullanıcı Sil</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                <span className="font-mono font-bold text-red-600 dark:text-red-400">{deleteUsername}</span> kullanıcısını silmek istediğinize emin misiniz?
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={handleDeleteUser}
                  className="flex-1 bg-red-600 text-white py-2 rounded-md hover:bg-red-700 text-sm"
                >
                  Sil
                </button>
                <button
                  onClick={() => { setDeleteUserId(null); setDeleteUsername(''); }}
                  className="flex-1 bg-gray-400 text-white py-2 rounded-md hover:bg-gray-500 text-sm"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Kullanıcı Tablosu */}
        {loading ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">Yükleniyor...</div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Kullanıcı</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Ad Soyad</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Rol</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Depo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">İstasyon</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Durum</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">İşlem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-gray-100">{user.username}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{user.full_name || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-1 rounded-full ${roleColor(user.role)}`}>
                        {roleLabel(user.role)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                      {user.depot_name ? `${user.depot_name} (${user.depot_code})` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{user.station_name || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggleActive(user)}
                        className={`text-xs px-2 py-1 rounded-full ${
                          user.is_active
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                        }`}
                      >
                        {user.is_active ? 'Aktif' : 'Pasif'}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center space-x-2">
                        <button
                          onClick={() => openEditDialog(user)}
                          className="text-blue-600 dark:text-blue-400 hover:underline text-xs"
                        >
                          Düzenle
                        </button>
                        <button
                          onClick={() => setResetUserId(user.id)}
                          className="text-yellow-600 dark:text-yellow-400 hover:underline text-xs"
                        >
                          Şifre Sıfırla
                        </button>
                        {user.role !== 'superadmin' && (
                          <button
                            onClick={() => { setDeleteUserId(user.id); setDeleteUsername(user.username); }}
                            className="text-red-600 dark:text-red-400 hover:underline text-xs"
                          >
                            Sil
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                Kullanıcı bulunamadı
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
