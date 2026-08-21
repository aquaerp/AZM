import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, Alert, AppState, FlatList, Pressable, RefreshControl, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import { StatusBar } from 'expo-status-bar'

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL || 'https://tidesight.cloud/api').replace(/\/$/, '')
const WEBSOCKET_URL = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
const REFRESH_INTERVAL = 10_000
const TOKEN_KEY = 'azm_mobile_access_token'
const REFRESH_KEY = 'azm_mobile_refresh_token'

const statusColor = { pending: '#d97706', in_progress: '#2563eb', ready: '#15803d', delivered: '#4f46e5', cancelled: '#b91c1c' }
const taskColor = { not_started: '#64748b', in_progress: '#2563eb', completed: '#15803d', cancelled: '#b91c1c' }

function displayError(error) {
  if (error?.message) return error.message
  return 'تعذر إتمام العملية. تحقق من الاتصال ثم حاول مجدداً.'
}

async function api(path, { method = 'GET', token, body, retried = false } = {}) {
  if (!API_BASE_URL) throw new Error('لم يتم ضبط عنوان واجهة النظام. أضف EXPO_PUBLIC_API_BASE_URL في ملف .env.')
  const storedToken = token ? await SecureStore.getItemAsync(TOKEN_KEY) : null
  const activeToken = storedToken || token
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { Accept: 'application/json', 'Accept-Language': 'ar', ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const data = await response.json().catch(() => ({}))
  if (response.status === 401 && activeToken && !retried && path !== '/auth/token/refresh/') {
    const refresh = await SecureStore.getItemAsync(REFRESH_KEY)
    if (refresh) {
      const refreshed = await fetch(`${API_BASE_URL}/auth/token/refresh/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh }) })
      const refreshedData = await refreshed.json().catch(() => ({}))
      if (refreshed.ok && refreshedData.access) {
        await SecureStore.setItemAsync(TOKEN_KEY, refreshedData.access)
        return api(path, { method, token: refreshedData.access, body, retried: true })
      }
    }
    await SecureStore.deleteItemAsync(TOKEN_KEY)
    await SecureStore.deleteItemAsync(REFRESH_KEY)
    throw new Error('انتهت جلسة الدخول. يرجى تسجيل الدخول مرة أخرى.')
  }
  if (!response.ok) {
    const message = typeof data === 'string' ? data : Object.values(data).flat().join('\n') || 'تعذر إتمام الطلب.'
    throw new Error(message)
  }
  return data
}

function PrimaryButton({ title, onPress, disabled = false, subtle = false }) {
  return <Pressable onPress={onPress} disabled={disabled} style={[styles.button, subtle && styles.buttonSubtle, disabled && styles.buttonDisabled]}><Text style={[styles.buttonText, subtle && styles.buttonTextSubtle]}>{title}</Text></Pressable>
}

function Pill({ label, color }) {
  return <View style={[styles.pill, { backgroundColor: `${color}18` }]}><Text style={[styles.pillText, { color }]}>{label}</Text></View>
}

function Login({ onAuthenticated }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const login = async () => {
    setLoading(true)
    try {
      const tokens = await api('/auth/login/', { method: 'POST', body: { username, password } })
      await SecureStore.setItemAsync(TOKEN_KEY, tokens.access)
      await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh)
      const user = await api('/auth/me/', { token: tokens.access })
      onAuthenticated({ user, token: tokens.access })
    } catch (error) {
      Alert.alert('تعذر تسجيل الدخول', displayError(error))
    } finally {
      setLoading(false)
    }
  }

  return <SafeAreaView style={styles.safe}><StatusBar style="light" /><View style={styles.loginShell}><View style={styles.brand}><Text style={styles.brandMark}>ع</Text><Text style={styles.brandTitle}>عزم</Text><Text style={styles.brandSubtitle}>إدارة الورشة من الميدان</Text></View><View style={styles.loginCard}><Text style={styles.loginTitle}>تسجيل الدخول</Text><Text style={styles.loginHint}>استخدم حسابك الحالي في نظام عزم.</Text><TextInput value={username} onChangeText={setUsername} placeholder="اسم المستخدم" placeholderTextColor="#94a3b8" autoCapitalize="none" style={styles.input} textAlign="right" /><TextInput value={password} onChangeText={setPassword} placeholder="كلمة المرور" placeholderTextColor="#94a3b8" secureTextEntry style={styles.input} textAlign="right" onSubmitEditing={login} /><PrimaryButton title={loading ? 'جارٍ التحقق...' : 'دخول'} onPress={login} disabled={loading || !username || !password} />{!API_BASE_URL && <Text style={styles.configWarning}>يلزم ضبط EXPO_PUBLIC_API_BASE_URL قبل الاستخدام.</Text>}</View></View></SafeAreaView>
}

function JobCard({ item, onSelect }) {
  const color = statusColor[item.status] || '#475569'
  return <Pressable onPress={() => onSelect(item)} style={styles.card}><View style={styles.cardTop}><View><Text style={styles.cardNumber}>{item.job_number}</Text><Text style={styles.cardVehicle}>{item.vehicle_label}</Text></View><Pill label={item.status_label} color={color} /></View><Text style={styles.cardCustomer}>{item.customer_name}</Text><Text numberOfLines={2} style={styles.cardDescription}>{item.complaint}</Text>{item.promised_at && <Text style={styles.cardMeta}>موعد الإنجاز: {new Date(item.promised_at).toLocaleString('ar-SA')}</Text>}</Pressable>
}

function JobDetails({ job, role, token, onSaved }) {
  const [diagnosis, setDiagnosis] = useState(job.diagnosis || '')
  const [saving, setSaving] = useState(false)
  const canUpdate = role === 'technician' || role === 'manager' || role === 'owner'
  const choices = role === 'technician' ? [['in_progress', 'بدء الإصلاح'], ['ready', 'تجهيز للاستلام']] : [['in_progress', 'قيد الإصلاح'], ['ready', 'جاهزة'], ['delivered', 'تم التسليم']]

  const update = async (status) => {
    setSaving(true)
    try {
      await api(`/workshop/job-cards/${job.id}/status/`, { method: 'PATCH', token, body: { status, diagnosis } })
      Alert.alert('تم الحفظ', 'تم تحديث بطاقة العمل لجميع المستخدمين.')
      onSaved()
    } catch (error) {
      Alert.alert('تعذر تحديث البطاقة', displayError(error))
    } finally {
      setSaving(false)
    }
  }

  return <View style={styles.detail}><View style={styles.detailHeader}><Text style={styles.sectionTitle}>تفاصيل البطاقة {job.job_number}</Text><Pill label={job.status_label} color={statusColor[job.status] || '#475569'} /></View><Text style={styles.detailLine}>المركبة: {job.vehicle_label}</Text><Text style={styles.detailLine}>العميل: {job.customer_name}</Text><Text style={styles.detailComplaint}>{job.complaint}</Text>{canUpdate ? <><Text style={styles.fieldLabel}>نتيجة الفحص أو التحديث</Text><TextInput value={diagnosis} onChangeText={setDiagnosis} multiline placeholder="أدخل ما تم إنجازه أو نتيجة الفحص" placeholderTextColor="#94a3b8" textAlign="right" style={[styles.input, styles.multiline]} /> <View style={styles.actionRow}>{choices.map(([status, label]) => <PrimaryButton key={status} title={saving ? 'جارٍ الحفظ...' : label} onPress={() => update(status)} disabled={saving || job.status === status} subtle={status !== 'ready'} />)}</View></> : <Text style={styles.readOnly}>حسابك للعرض والمتابعة فقط.</Text>}</View>
}

function TaskCard({ item, role, token, onSaved }) {
  const [saving, setSaving] = useState(false)
  const canAct = role === 'technician' || role === 'manager' || role === 'owner'
  const action = item.status === 'not_started' ? ['start', 'بدء المهمة'] : item.status === 'in_progress' ? ['complete', 'إكمال المهمة'] : null
  const submit = async () => {
    if (!action) return
    setSaving(true)
    try {
      await api(`/workforce/tasks/${item.id}/${action[0]}/`, { method: 'POST', token })
      onSaved()
    } catch (error) {
      Alert.alert('تعذر تحديث المهمة', displayError(error))
    } finally { setSaving(false) }
  }
  return <View style={styles.task}><View style={styles.cardTop}><View><Text style={styles.taskTitle}>{item.title}</Text><Text style={styles.taskMeta}>{item.job_number} · {item.employee_name}</Text></View><Pill label={item.status_label} color={taskColor[item.status] || '#475569'} /></View>{item.description ? <Text style={styles.cardDescription}>{item.description}</Text> : null}{action && canAct && <PrimaryButton title={saving ? 'جارٍ الحفظ...' : action[1]} onPress={submit} disabled={saving} subtle={action[0] === 'start'} />}</View>
}

function Workspace({ session, onLogout }) {
  const [jobs, setJobs] = useState([])
  const [tasks, setTasks] = useState([])
  const [selectedJob, setSelectedJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [liveConnected, setLiveConnected] = useState(false)
  const appState = useRef(AppState.currentState)
  const roleLabel = { owner: 'مالك الورشة', manager: 'مدير الورشة', technician: 'فني', accountant: 'محاسب', receptionist: 'موظف استقبال' }[session.user.role] || session.user.role

  const refresh = useCallback(async (manual = false) => {
    manual ? setRefreshing(true) : setLoading(true)
    try {
      const [jobData, taskData] = await Promise.all([api('/workshop/job-cards/', { token: session.token }), api('/workforce/tasks/', { token: session.token })])
      setJobs(jobData)
      setTasks(taskData)
      setUpdatedAt(new Date())
      setSelectedJob((current) => current ? jobData.find((job) => job.id === current.id) || null : null)
    } catch (error) {
      if (manual) Alert.alert('تعذر التحديث', displayError(error))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [session.token])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const timer = setInterval(() => refresh(), REFRESH_INTERVAL)
    const subscription = AppState.addEventListener('change', (next) => {
      if (appState.current.match(/inactive|background/) && next === 'active') refresh(true)
      appState.current = next
    })
    return () => { clearInterval(timer); subscription.remove() }
  }, [refresh])
  useEffect(() => {
    if (!WEBSOCKET_URL) return undefined
    const socket = new WebSocket(`${WEBSOCKET_URL}/ws/workshop/updates/`, ['azm', `jwt.${session.token}`])
    socket.onopen = () => setLiveConnected(true)
    socket.onmessage = () => refresh()
    socket.onerror = () => setLiveConnected(false)
    socket.onclose = () => setLiveConnected(false)
    return () => socket.close()
  }, [refresh, session.token])

  const counts = jobs.reduce((all, job) => ({ ...all, [job.status]: (all[job.status] || 0) + 1 }), {})
  if (loading && !updatedAt) return <SafeAreaView style={styles.safe}><StatusBar style="light" /><View style={styles.loader}><ActivityIndicator color="#f8fafc" size="large" /><Text style={styles.loaderText}>جارٍ تحميل بيانات الورشة...</Text></View></SafeAreaView>
  return <SafeAreaView style={styles.safe}><StatusBar style="light" /><FlatList data={jobs} keyExtractor={(item) => String(item.id)} renderItem={({ item }) => <JobCard item={item} onSelect={setSelectedJob} />} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => refresh(true)} tintColor="#fff" />} contentContainerStyle={styles.list} ListHeaderComponent={<><View style={styles.header}><View><Text style={styles.greeting}>مرحباً {session.user.first_name || session.user.username}</Text><Text style={styles.role}>{roleLabel} · {session.user.workshop?.name}</Text></View><Pressable onPress={onLogout}><Text style={styles.logout}>خروج</Text></Pressable></View><Text style={styles.sync}>{liveConnected ? 'التزامن اللحظي متصل' : 'التزامن اللحظي غير متصل — التحديث الاحتياطي كل 10 ثوانٍ'}{updatedAt ? ` · آخر تحديث ${updatedAt.toLocaleTimeString('ar-SA')}` : ''}</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.counts}>{Object.entries({ pending: 'بانتظار الفحص', in_progress: 'قيد الإصلاح', ready: 'جاهزة', delivered: 'تم التسليم' }).map(([status, label]) => <View key={status} style={styles.count}><Text style={[styles.countValue, { color: statusColor[status] }]}>{counts[status] || 0}</Text><Text style={styles.countLabel}>{label}</Text></View>)}</ScrollView>{selectedJob && <JobDetails job={selectedJob} role={session.user.role} token={session.token} onSaved={() => refresh(true)} />}<View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{session.user.role === 'technician' ? 'بطاقات العمل المسندة إليك' : 'بطاقات العمل'}</Text><Text style={styles.sectionCount}>{jobs.length}</Text></View></>} ListEmptyComponent={<Text style={styles.empty}>لا توجد بطاقات عمل متاحة.</Text>} ListFooterComponent={<View><View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{session.user.role === 'technician' ? 'مهامي' : 'مهام الفريق'}</Text><Text style={styles.sectionCount}>{tasks.length}</Text></View>{tasks.map((task) => <TaskCard key={task.id} item={task} role={session.user.role} token={session.token} onSaved={() => refresh(true)} />)}{tasks.length === 0 && <Text style={styles.empty}>لا توجد مهام متاحة.</Text>}</View>} /></SafeAreaView>
}

export default function App() {
  const [session, setSession] = useState(null)
  const [checking, setChecking] = useState(true)
  useEffect(() => {
    const restore = async () => {
      try {
        const token = await SecureStore.getItemAsync(TOKEN_KEY)
        if (token) setSession({ token, user: await api('/auth/me/', { token }) })
      } catch { await SecureStore.deleteItemAsync(TOKEN_KEY); await SecureStore.deleteItemAsync(REFRESH_KEY) } finally { setChecking(false) }
    }
    restore()
  }, [])
  const logout = async () => { await SecureStore.deleteItemAsync(TOKEN_KEY); await SecureStore.deleteItemAsync(REFRESH_KEY); setSession(null) }
  if (checking) return <SafeAreaView style={styles.safe}><StatusBar style="light" /><View style={styles.loader}><ActivityIndicator color="#fff" size="large" /></View></SafeAreaView>
  return session ? <Workspace session={session} onLogout={logout} /> : <Login onAuthenticated={setSession} />
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0f172a' }, loader: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 14 }, loaderText: { color: '#e2e8f0', fontSize: 16 }, loginShell: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#0f172a' }, brand: { alignItems: 'center', marginBottom: 34 }, brandMark: { color: '#fff', backgroundColor: '#0ea5a4', width: 66, height: 66, borderRadius: 33, textAlign: 'center', textAlignVertical: 'center', fontSize: 36, fontWeight: '800' }, brandTitle: { color: '#fff', fontSize: 34, fontWeight: '800', marginTop: 10 }, brandSubtitle: { color: '#94a3b8', fontSize: 15, marginTop: 4 }, loginCard: { backgroundColor: '#fff', borderRadius: 20, padding: 20, gap: 12 }, loginTitle: { color: '#0f172a', fontSize: 22, textAlign: 'right', fontWeight: '800' }, loginHint: { color: '#64748b', textAlign: 'right', marginBottom: 6 }, input: { backgroundColor: '#f8fafc', color: '#0f172a', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 13, fontSize: 16 }, multiline: { minHeight: 86, textAlignVertical: 'top' }, button: { backgroundColor: '#0f766e', borderRadius: 11, paddingVertical: 12, paddingHorizontal: 16, alignItems: 'center', marginTop: 6 }, buttonSubtle: { backgroundColor: '#e0f2fe' }, buttonDisabled: { opacity: 0.5 }, buttonText: { color: '#fff', fontWeight: '800', fontSize: 15 }, buttonTextSubtle: { color: '#075985' }, configWarning: { color: '#b45309', textAlign: 'right', lineHeight: 20 }, list: { padding: 16, paddingBottom: 34, backgroundColor: '#f1f5f9' }, header: { backgroundColor: '#0f172a', marginHorizontal: -16, marginTop: -16, padding: 20, paddingTop: 24, flexDirection: 'row-reverse', justifyContent: 'space-between', alignItems: 'center' }, greeting: { color: '#fff', fontSize: 21, fontWeight: '800', textAlign: 'right' }, role: { color: '#94a3b8', marginTop: 4, textAlign: 'right' }, logout: { color: '#5eead4', fontWeight: '700' }, sync: { color: '#64748b', textAlign: 'right', paddingVertical: 12, fontSize: 12 }, counts: { gap: 9, paddingBottom: 12, flexDirection: 'row-reverse' }, count: { backgroundColor: '#fff', padding: 12, borderRadius: 12, minWidth: 108, elevation: 1 }, countValue: { fontSize: 24, fontWeight: '800', textAlign: 'right' }, countLabel: { color: '#64748b', fontSize: 12, marginTop: 4, textAlign: 'right' }, sectionHeader: { flexDirection: 'row-reverse', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, marginBottom: 8 }, sectionTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a', textAlign: 'right' }, sectionCount: { color: '#64748b', backgroundColor: '#e2e8f0', borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 }, card: { backgroundColor: '#fff', borderRadius: 14, padding: 15, marginBottom: 10, borderWidth: 1, borderColor: '#e2e8f0' }, cardTop: { flexDirection: 'row-reverse', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }, cardNumber: { color: '#0f172a', fontSize: 16, fontWeight: '800', textAlign: 'right' }, cardVehicle: { color: '#475569', marginTop: 2, textAlign: 'right' }, cardCustomer: { color: '#334155', marginTop: 10, textAlign: 'right', fontWeight: '600' }, cardDescription: { color: '#64748b', marginTop: 5, lineHeight: 20, textAlign: 'right' }, cardMeta: { color: '#64748b', marginTop: 8, fontSize: 12, textAlign: 'right' }, pill: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 20 }, pillText: { fontSize: 12, fontWeight: '700' }, detail: { backgroundColor: '#ecfeff', borderRadius: 14, padding: 15, borderWidth: 1, borderColor: '#99f6e4', marginBottom: 10 }, detailHeader: { flexDirection: 'row-reverse', justifyContent: 'space-between', alignItems: 'center', gap: 8 }, detailLine: { color: '#334155', textAlign: 'right', marginTop: 9 }, detailComplaint: { color: '#0f172a', textAlign: 'right', marginTop: 10, lineHeight: 21 }, fieldLabel: { color: '#0f172a', textAlign: 'right', fontWeight: '700', marginTop: 14, marginBottom: 6 }, actionRow: { gap: 8, marginTop: 8 }, readOnly: { color: '#64748b', textAlign: 'right', marginTop: 12 }, task: { backgroundColor: '#fff', borderRadius: 14, padding: 15, marginBottom: 10, borderWidth: 1, borderColor: '#e2e8f0' }, taskTitle: { color: '#0f172a', fontWeight: '800', fontSize: 16, textAlign: 'right' }, taskMeta: { color: '#64748b', marginTop: 3, fontSize: 12, textAlign: 'right' }, empty: { color: '#64748b', backgroundColor: '#fff', borderRadius: 12, padding: 18, textAlign: 'center' },
})
