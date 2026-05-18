import { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { supabase } from '../lib/supabase';

export function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');

  async function handleSubmit() {
    if (!email || !password) {
      Alert.alert('Preencha email e senha');
      return;
    }
    setSubmitting(true);
    try {
      if (mode === 'sign-in') {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        Alert.alert(
          'Conta criada',
          'Se a confirmacao por email estiver ativada no Supabase, verifique seu email antes de entrar.'
        );
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido';
      Alert.alert('Erro', message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Text style={styles.title}>Inventario</Text>
      <Text style={styles.subtitle}>
        {mode === 'sign-in' ? 'Entrar na sua conta' : 'Criar uma conta nova'}
      </Text>

      <TextInput
        style={styles.input}
        placeholder="email@exemplo.com"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="senha"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <Pressable
        style={[styles.button, submitting && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        <Text style={styles.buttonText}>
          {submitting ? 'Aguarde...' : mode === 'sign-in' ? 'Entrar' : 'Cadastrar'}
        </Text>
      </Pressable>

      <Pressable
        onPress={() => setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in')}
        style={styles.switchMode}
      >
        <Text style={styles.link}>
          {mode === 'sign-in' ? 'Nao tem conta? Cadastre-se' : 'Ja tem conta? Entrar'}
        </Text>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  title: { fontSize: 32, fontWeight: '700', textAlign: 'center', marginBottom: 8 },
  subtitle: { fontSize: 16, textAlign: 'center', marginBottom: 32, color: '#666' },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#2563eb',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  switchMode: { marginTop: 16, alignItems: 'center' },
  link: { color: '#2563eb' },
});
