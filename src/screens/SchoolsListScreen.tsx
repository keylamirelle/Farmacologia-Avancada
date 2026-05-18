import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSchools } from '../hooks/useSchools';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function SchoolsListScreen() {
  const nav = useNavigation<Nav>();
  const { schools, loading, refresh } = useSchools();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return schools;
    return schools.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        (s.city ? s.city.toLowerCase().includes(q) : false)
    );
  }, [schools, search]);

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <TextInput
          style={styles.search}
          placeholder="Buscar escola"
          value={search}
          onChangeText={setSearch}
          autoCapitalize="none"
        />
        <Pressable style={styles.addBtn} onPress={() => nav.navigate('SchoolForm', {})}>
          <Text style={styles.addBtnText}>+ Nova</Text>
        </Pressable>
      </View>

      {loading && schools.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(s) => s.id}
          contentContainerStyle={{ padding: 16, paddingTop: 0 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => (
            <Pressable
              style={[styles.card, !item.active && styles.cardInactive]}
              onPress={() => nav.navigate('SchoolForm', { id: item.id })}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.name}</Text>
                {item.city ? <Text style={styles.sub}>{item.city}</Text> : null}
              </View>
              {!item.active && <Text style={styles.inactiveTag}>inativa</Text>}
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              Nenhuma escola cadastrada. Toque em &quot;+ Nova&quot;.
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  headerRow: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 8 },
  search: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 10,
    backgroundColor: '#fff',
  },
  addBtn: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  addBtnText: { color: '#fff', fontWeight: '600' },
  card: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardInactive: { opacity: 0.6 },
  name: { fontSize: 16, fontWeight: '600' },
  sub: { fontSize: 13, color: '#6b7280', marginTop: 2 },
  inactiveTag: {
    color: '#991b1b',
    fontSize: 11,
    fontWeight: '600',
    backgroundColor: '#fee2e2',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  empty: { textAlign: 'center', marginTop: 32, color: '#6b7280' },
});
