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
import { usePeople } from '../hooks/usePeople';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function PeopleListScreen() {
  const nav = useNavigation<Nav>();
  const { people, loading, refresh } = usePeople();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return people;
    return people.filter((p) => p.name.toLowerCase().includes(q));
  }, [people, search]);

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <TextInput
          style={styles.search}
          placeholder="Buscar pessoa"
          value={search}
          onChangeText={setSearch}
          autoCapitalize="none"
        />
        <Pressable
          style={styles.addBtn}
          onPress={() => nav.navigate('PersonForm', {})}
        >
          <Text style={styles.addBtnText}>+ Nova</Text>
        </Pressable>
      </View>

      {loading && people.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ padding: 16, paddingTop: 0 }}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} />}
          renderItem={({ item }) => (
            <Pressable
              style={[styles.card, !item.active && styles.cardInactive]}
              onPress={() => nav.navigate('PersonForm', { id: item.id })}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.name}</Text>
                {item.role ? <Text style={styles.sub}>{item.role}</Text> : null}
                {item.phone ? <Text style={styles.sub}>{item.phone}</Text> : null}
              </View>
              {!item.active && <Text style={styles.inactiveTag}>inativa</Text>}
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              Nenhuma pessoa cadastrada. Toque em &quot;+ Nova&quot;.
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 8,
  },
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
