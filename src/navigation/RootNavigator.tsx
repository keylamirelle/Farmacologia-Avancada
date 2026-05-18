import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { MaterialFormScreen } from '../screens/MaterialFormScreen';
import { MaterialsListScreen } from '../screens/MaterialsListScreen';
import { NewWithdrawalScreen } from '../screens/NewWithdrawalScreen';
import { PeopleListScreen } from '../screens/PeopleListScreen';
import { PersonFormScreen } from '../screens/PersonFormScreen';
import { SchoolFormScreen } from '../screens/SchoolFormScreen';
import { SchoolsListScreen } from '../screens/SchoolsListScreen';
import { AppTabs } from './AppTabs';

export type RootStackParamList = {
  Tabs: undefined;
  NewWithdrawal: undefined;
  PeopleList: undefined;
  PersonForm: { id?: string };
  SchoolsList: undefined;
  SchoolForm: { id?: string };
  MaterialsList: undefined;
  MaterialForm: { id?: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Tabs" component={AppTabs} options={{ headerShown: false }} />
        <Stack.Screen
          name="NewWithdrawal"
          component={NewWithdrawalScreen}
          options={{ title: 'Nova retirada' }}
        />
        <Stack.Screen name="PeopleList" component={PeopleListScreen} options={{ title: 'Pessoas' }} />
        <Stack.Screen
          name="PersonForm"
          component={PersonFormScreen}
          options={({ route }) => ({ title: route.params?.id ? 'Editar pessoa' : 'Nova pessoa' })}
        />
        <Stack.Screen name="SchoolsList" component={SchoolsListScreen} options={{ title: 'Escolas' }} />
        <Stack.Screen
          name="SchoolForm"
          component={SchoolFormScreen}
          options={({ route }) => ({ title: route.params?.id ? 'Editar escola' : 'Nova escola' })}
        />
        <Stack.Screen
          name="MaterialsList"
          component={MaterialsListScreen}
          options={{ title: 'Materiais' }}
        />
        <Stack.Screen
          name="MaterialForm"
          component={MaterialFormScreen}
          options={({ route }) => ({ title: route.params?.id ? 'Editar material' : 'Novo material' })}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
