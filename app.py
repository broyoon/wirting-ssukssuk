import os, json, base64, io
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title='글쓰기 쑥쑥!',page_icon='✏️',layout='centered')
st.markdown('''<style>.stApp{background:#fcfaf5}h1{color:#27675a}.stButton button{border-radius:14px;font-weight:700}div[data-testid="stMetricValue"]{color:#27675a}</style>''',unsafe_allow_html=True)
st.title('✏️ 글쓰기 쑥쑥!')
st.write('내가 쓴 글을 사진으로 찍고, 잘한 점과 더 멋지게 쓸 방법을 알아봐요!')
key=st.secrets.get('GEMINI_API_KEY',os.getenv('GEMINI_API_KEY',''))
if not key:
 st.warning('선생님이 먼저 GEMINI_API_KEY를 설정해야 사진 읽기와 평가 기능을 사용할 수 있어요.')
 st.stop()
client=genai.Client(api_key=key)
criteria=['일의 순서나 방법이 잘 드러나게 썼나요?','읽는 사람이 궁금해할 내용으로 썼나요?','바르고 정확한 문장으로 썼나요?','이어주는 말 또는 순서를 드러내는 말을 적절하게 사용했나요?','글의 짜임에 맞게 문단을 잘 나눴나요?']
name=st.text_input('별명 (실명은 쓰지 않아도 돼요)',max_chars=20)
subject=st.text_input('글의 주제 (선택)',placeholder='예: 샌드위치 만드는 방법')
photo=st.camera_input('📷 글을 사진으로 찍어요')
file=st.file_uploader('또는 사진 파일을 올려요',type=['png','jpg','jpeg'])
image_file=photo or file
if image_file:
 raw=image_file.getvalue()
 if len(raw)>12_000_000: st.error('사진 크기를 12MB 이하로 줄여 주세요.'); st.stop()
 img=Image.open(io.BytesIO(raw)).convert('RGB'); img.thumbnail((1600,1600))
 st.image(img,caption='올린 글 사진',use_container_width=True)
 buf=io.BytesIO();img.save(buf,format='JPEG',quality=85)
 encoded=base64.b64encode(buf.getvalue()).decode()
 fingerprint=str(hash(buf.getvalue()))
 if st.session_state.get('fingerprint')!=fingerprint:
  st.session_state.fingerprint=fingerprint
  st.session_state.pop('recognized',None)
  st.session_state.pop('result',None)
 if st.button('🔎 사진 속 글 읽기',disabled=not bool(key)):
  with st.spinner('손글씨를 읽고 있어요...'):
   try:
    resp=client.models.generate_content(model='gemini-2.5-flash',contents=[types.Part.from_text(text='사진의 한글 손글씨를 그대로 옮겨 주세요. 맞춤법을 수정하지 말고 문단과 줄바꿈을 최대한 유지하세요. 읽을 수 없는 글자는 [판독불가]로 적으세요. 전사문만 출력하세요.'),types.Part.from_bytes(data=buf.getvalue(),mime_type='image/jpeg')])
    st.session_state.recognized=resp.text
   except Exception as e: st.error('사진을 읽지 못했어요. 잠시 후 다시 시도해 주세요.')
 if 'recognized' in st.session_state:
  st.info('AI가 잘못 읽은 글자는 고쳐 주세요. 문단 사이에는 빈 줄을 남겨 주세요.')
  edited=st.text_area('📝 사진에서 읽은 글',value=st.session_state.recognized,height=270)
  if st.button('🌟 내 글 평가받기',type='primary'):
   if len(edited.strip())<15: st.warning('글이 너무 짧거나 판독되지 않았어요. 사진과 글자를 확인해 주세요.')
   else:
    with st.spinner('글을 꼼꼼하게 읽고 있어요...'):
     try:
      prompt='''초등학교 3학년 학생의 '일의 순서나 방법을 설명하는 글'을 평가하세요. 반드시 원문 근거로 평가하고 없는 내용을 만들어내지 마세요. 다음 5개 기준을 각각 0,5,10,15,20점 중 하나로 채점하세요: 1 순서/방법의 명확성 2 독자가 궁금해할 정보의 충실성 3 바르고 정확한 문장 4 연결/순서 표현의 적절성 5 글의 짜임에 맞는 문단 구분. 글의 길이 자체에 가산점 주지 마세요. 손글씨 판독 오류일 가능성이 있는 부분은 단정해 감점하지 마세요. 빈 줄로 구분된 문단을 고려하세요. 각 기준마다 어린이가 이해할 수 있는 근거 1문장과 실천 가능한 제안 1문장을 작성하세요. 잘한 점 1~2문장, 다음에 고칠 점 1~2문장을 따뜻하되 정확하게 작성하세요. 학생의 신상이나 이름을 추측하지 마세요. JSON 객체만 반환하세요. 형식: {"scores":[{"score":15,"reason":"...","tip":"..."} 다섯 개],"praise":"...","next_step":"..."}.'''
      resp=client.models.generate_content(model='gemini-2.5-flash',contents=prompt+'\n\n글의 주제: '+(subject or '미지정')+'\n학생 글 원문:\n'+edited,config=types.GenerateContentConfig(response_mime_type='application/json',temperature=0.2))
      data=json.loads(resp.text)
      scores=data['scores']
      if len(scores)!=5 or any(type(x['score'])!=int or x['score'] not in (0,5,10,15,20) for x in scores): raise ValueError('Invalid rubric')
      st.session_state.result=data
     except Exception: st.error('평가 결과를 만들지 못했어요. 다시 시도해 주세요.')
  if 'result' in st.session_state:
   result=st.session_state.result
   st.divider();st.subheader('🎉 나의 글쓰기 성장 카드')
   total=sum(x['score'] for x in result['scores']);st.metric('총점',f'{total} / 100점');st.progress(total/100)
   for i,(criterion,item) in enumerate(zip(criteria,result['scores'])):
    with st.expander(f'{i+1}. {criterion} — {item["score"]}/20점',expanded=True):
     st.write('👍',item['reason']);st.write('✍️',item['tip'])
   st.success('💚 잘한 점: '+result['praise'])
   st.info('🌱 다음에 도전할 점: '+result['next_step'])
   st.caption('AI 평가 결과는 참고용이에요. 선생님이 확인하면 더 정확해요.')
   st.download_button('📄 결과 저장하기',data=(f'글쓰기 쑥쑥! {name}\n총점 {total}/100\n\n'+ '\n'.join(f'{c} {r["score"]}/20\n{r["reason"]}\n{r["tip"]}' for c,r in zip(criteria,result['scores']))+f'\n\n잘한 점: {result["praise"]}\n다음 목표: {result["next_step"]}').encode('utf-8-sig'),file_name='글쓰기_평가결과.txt',mime='text/plain')
st.caption('개인정보 보호: 사진에 학생 이름, 얼굴, 학교 정보가 보이지 않게 촬영하세요. 이미지는 AI 판독을 위해 외부 API로 전송됩니다. 교실 사용 전 보호자 동의 및 학교 개인정보 처리 기준을 확인하세요.')
