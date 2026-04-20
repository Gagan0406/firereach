import { useState, useCallback } from 'react'
import { runAgent } from '../utils/api'

const INITIAL_FORM = { icp: '', company: '', email: '' }

const INITIAL_RESULT = {
  session_id: null,
  status: 'idle',
  signals: {},
  research_brief: '',
  email_subject: '',
  email_body: '',
  error: null,
  chat_history: [],
}

export function useFireReach() {
  const [form, setForm]       = useState(INITIAL_FORM)
  const [result, setResult]   = useState(INITIAL_RESULT)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors]   = useState({})

  const validate = useCallback(() => {
    const e = {}
    if (!form.icp.trim() || form.icp.trim().length < 10)
      e.icp = 'ICP must be at least 10 characters'
    if (!form.company.trim())
      e.company = 'Company name is required'
    if (!form.email.trim() || !form.email.includes('@'))
      e.email = 'Valid email address required'
    setErrors(e)
    return Object.keys(e).length === 0
  }, [form])

  const handleChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setErrors(prev => ({ ...prev, [field]: undefined }))
  }, [])

  const handleRun = useCallback(async () => {
    if (!validate()) return
    setLoading(true)
    setResult({ ...INITIAL_RESULT, status: 'running' })

    try {
      const data = await runAgent(form)
      setResult({
        session_id:     data.session_id,
        status:         data.status,
        signals:        data.signals || {},
        research_brief: data.research_brief || '',
        email_subject:  data.email_subject || '',
        email_body:     data.email_body || '',
        error:          data.error || null,
        chat_history:   data.chat_history || [],
      })
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Unknown error'
      setResult(prev => ({ ...prev, status: 'failed', error: msg }))
    } finally {
      setLoading(false)
    }
  }, [form, validate])

  const handleReset = useCallback(() => {
    setForm(INITIAL_FORM)
    setResult(INITIAL_RESULT)
    setErrors({})
  }, [])

  return {
    form, handleChange,
    result,
    loading,
    errors,
    handleRun,
    handleReset,
  }
}
