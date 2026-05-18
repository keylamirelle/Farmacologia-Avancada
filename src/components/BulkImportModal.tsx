import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

export function BulkImportModal({
  visible,
  onClose,
  title,
  placeholder,
  hint,
  onImport,
}: {
  visible: boolean;
  onClose: () => void;
  title: string;
  placeholder: string;
  hint: string;
  onImport: (names: string[]) => Promise<{ inserted: number; error?: string }>;
}) {
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const parsedNames = useMemo(
    () =>
      text
        .split('\n')
        .map((l) => l.trim())
        .filter((l) => l.length > 0),
    [text]
  );

  async function submit() {
    if (parsedNames.length === 0) {
      Alert.alert('Lista vazia', 'Cole pelo menos um nome (um por linha).');
      return;
    }
    setSubmitting(true);
    const result = await onImport(parsedNames);
    setSubmitting(false);
    if (result.error) {
      Alert.alert('Erro ao importar', result.error);
      return;
    }
    Alert.alert(
      'Pronto',
      `${result.inserted} item(s) adicionado(s) com sucesso.`,
      [
        {
          text: 'OK',
          onPress: () => {
            setText('');
            onClose();
          },
        },
      ]
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>{title}</Text>
          <Pressable onPress={onClose} disabled={submitting}>
            <Text style={styles.close}>Fechar</Text>
          </Pressable>
        </View>

        <View style={styles.body}>
          <Text style={styles.hint}>{hint}</Text>

          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder={placeholder}
            multiline
            autoCorrect={false}
            autoCapitalize="none"
            textAlignVertical="top"
          />

          <Text style={styles.counter}>
            {parsedNames.length} {parsedNames.length === 1 ? 'item' : 'itens'} pronto(s) para
            importar
          </Text>

          <Pressable
            style={[
              styles.submitBtn,
              (submitting || parsedNames.length === 0) && { opacity: 0.5 },
            ]}
            onPress={submit}
            disabled={submitting || parsedNames.length === 0}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitText}>
                Importar {parsedNames.length > 0 ? parsedNames.length : ''}
              </Text>
            )}
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  title: { fontSize: 18, fontWeight: '700' },
  close: { color: '#2563eb', fontWeight: '600' },
  body: { padding: 16, flex: 1 },
  hint: { color: '#374151', marginBottom: 12, fontSize: 14, lineHeight: 20 },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    minHeight: 220,
    backgroundColor: '#f9fafb',
    fontFamily: 'monospace',
  },
  counter: { marginTop: 8, color: '#6b7280', fontSize: 13 },
  submitBtn: {
    backgroundColor: '#2563eb',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 16,
  },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
