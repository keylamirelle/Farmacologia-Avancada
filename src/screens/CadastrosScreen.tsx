import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useMaterials } from '../hooks/useMaterials';
import { usePeople } from '../hooks/usePeople';
import { useSchools } from '../hooks/useSchools';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function CadastrosScreen() {
  const nav = useNavigation<Nav>();
  const { people } = usePeople();
  const { schools } = useSchools();
  const { materials } = useMaterials();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cadastros</Text>

      <MenuItem
        icon="P"
        label="Pessoas (responsáveis)"
        count={people.length}
        onPress={() => nav.navigate('PeopleList')}
      />
      <MenuItem
        icon="E"
        label="Escolas"
        count={schools.length}
        onPress={() => nav.navigate('SchoolsList')}
      />
      <MenuItem
        icon="M"
        label="Materiais"
        count={materials.length}
        onPress={() => nav.navigate('MaterialsList')}
      />
    </View>
  );
}

function MenuItem({
  icon,
  label,
  count,
  onPress,
}: {
  icon: string;
  label: string;
  count: number;
  onPress: () => void;
}) {
  return (
    <Pressable style={({ pressed }) => [styles.item, pressed && styles.pressed]} onPress={onPress}>
      <View style={styles.iconCircle}>
        <Text style={styles.iconText}>{icon}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.itemLabel}>{label}</Text>
        <Text style={styles.itemCount}>{count} cadastrados</Text>
      </View>
      <Text style={styles.chevron}>›</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9fafb' },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 16 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  pressed: { opacity: 0.7 },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#dbeafe',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  iconText: { fontSize: 18, fontWeight: '700', color: '#2563eb' },
  itemLabel: { fontSize: 16, fontWeight: '600' },
  itemCount: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  chevron: { fontSize: 24, color: '#9ca3af' },
});
