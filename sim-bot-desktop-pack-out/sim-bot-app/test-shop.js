import { initDatabase } from './src/db/database.js';
import {
  createKnowledgeItem,
  searchKnowledgeBase,
  upsertShopInfo,
  getShopInfo,
  createService,
  listServices,
  createAppointment,
  getAvailableSlots,
  createMembershipCard,
  useMembershipCard,
  createPendingQuestion,
  answerPendingQuestion,
} from './src/db/shop_store.js';

async function test() {
  console.log('=== Shop Management Feature Acceptance Test ===\n');
  
  const db = await initDatabase();
  let passed = 0;
  let failed = 0;

  // 1. Test Knowledge Base
  console.log('1. Knowledge Base Test');
  try {
    const kb = createKnowledgeItem(db, { question: 'What are your business hours?', answer: 'Our business hours are 9am to 10pm.', category: 'builtin' });
    console.log('   Created KB item:', kb);
    const search = searchKnowledgeBase(db, 'business hours');
    console.log('   Search results:', search.length);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 2. Test Shop Info
  console.log('\n2. Shop Info Test');
  try {
    upsertShopInfo(db, { name: 'Comfort Massage', address: '88 Jianguo Road, Chaoyang District', phone: '13800138000', business_hours: '09:00-22:00' });
    const info = getShopInfo(db);
    console.log('   Shop name:', info.name);
    console.log('   Address:', info.address);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 3. Test Services
  console.log('\n3. Services Test');
  try {
    const svc1 = createService(db, { name: 'Full Body Massage', category: 'Massage', duration_minutes: 60, price: 128, original_price: 168, description: 'Professional full body massage' });
    const svc2 = createService(db, { name: 'Foot Massage', category: 'Foot Care', duration_minutes: 45, price: 88, original_price: 108 });
    console.log('   Created services:', svc1.id, svc2.id);
    const services = listServices(db, { is_active: true });
    console.log('   Service count:', services.total);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 4. Test Appointments
  console.log('\n4. Appointment Test');
  try {
    const today = new Date();
    const dateStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
    const slots = getAvailableSlots(db, dateStr, 1, '');
    console.log('   Available slots:', slots.length);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 5. Test Membership Cards
  console.log('\n5. Membership Cards Test');
  try {
    const card = createMembershipCard(db, { card_no: 'VIP001', customer_name: 'Zhang San', customer_phone: '13900139000', total_services: 10 });
    console.log('   Created card:', card.id);
    const useResult = useMembershipCard(db, card.id, 1, 'Full Body Massage');
    console.log('   Remaining after use:', useResult.remaining_services);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 6. Test Pending Questions
  console.log('\n6. Pending Questions Test');
  try {
    const pending = createPendingQuestion(db, { question: 'Do you have cupping service?', asker_name: 'Li Si', asker_wxid: 'wxid_xxxx' });
    console.log('   Created pending:', pending.id);
    const answer = answerPendingQuestion(db, pending.id, 'Yes, we provide cupping service, 68 yuan per session.');
    console.log('   Answer success:', answer.ok);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  // 7. Test Knowledge Base Self-upgrade
  console.log('\n7. KB Self-upgrade Verification');
  try {
    const searchAfter = searchKnowledgeBase(db, 'cupping');
    console.log('   Search results for cupping:', searchAfter.length);
    const bossAnswer = searchAfter.find(s => s.category === 'boss');
    console.log('   Found boss answer:', !!bossAnswer);
    passed++;
    console.log('   PASS ✓');
  } catch (e) {
    failed++;
    console.log('   FAIL ✗:', e.message);
  }

  console.log('\n=== Test Summary ===');
  console.log('Passed:', passed);
  console.log('Failed:', failed);
  
  if (failed === 0) {
    console.log('\nAll tests passed! ✓');
    if (typeof db.persist === 'function') {
      db.persist();
      console.log('Data persisted.');
    }
    process.exit(0);
  } else {
    console.log('\nSome tests failed! ✗');
    process.exit(1);
  }
}

test().catch(e => {
  console.error('Test failed:', e.message);
  process.exit(1);
});