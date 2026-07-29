# auto_generate_vocab.py —— 逐词生成含全部字段的 3500 词库（替换 PLACEHOLDER 即可用）
import json, os, requests, time

DATA_DIR = os.path.join(os.getcwd(), "data")
VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

# 用你原来的完整单词列表替换下面的 PLACEHOLDER_WORD_LIST
WORD_STR = ("a,abandon,ability,able,abnormal,aboard,abolish,abortion,about,above,abroad,abrupt,absence,absent,absolute,absorb,abstract,absurd,abundant,abuse,"
 "academic,academy,accelerate,accent,accept,access,accessible,accident,accommodation,accompany,accomplish,account,accountant,accumulate,accuracy"
 "ache,achieve,achievement,acid,acknowledge,acquaintance,acquire,acquisition,acre,across,act,action,active,activity,actor,actress,actual,acute,adapt"
 "addicted,addition,address,adequate,adjust,adjustment,administration,admire,admission,admit,adolescence,adopt,adult,advance,advantage,adventure"
 "advocate,affair,affect,affection,afford,afraid,after,afternoon,afterward,again,against,age,agency,agenda,agent,aggressive,ago,agree,agreement"
 "agriculture,ahead,aid,aim,air,aircraft,airline,airmail,airplane,airport,alarm,album,alcohol,alcoholic,algebra,alike,alive,all,allergic,alley,"
 "allocate,allow,allowance,almost,alone,along,alongside,aloud,alphabet,already,also,alter,alternative,although,altitude,altogether,always,amateur,am"
 "ambassador,ambiguous,ambition,ambulance,among,amount,ample,amuse,amusement,analyse,analysis,ancestor,anchor,ancient,and,anger,angle,angry,animal"
 "anniversary,announce,announcement,annoy,annual,another,answer,ant,antarctic,antique,anxiety,anxious,any,anybody,anyhow,anyone,anything,anyway"
 "apart,apartment,apologize,apology,apparent,appeal,appear,appearance,appendix,appetite,applaud,apple,applicant,application,apply,appoint,appointment"
 "appropriate,approve,approximately,apron,arbitrary,arch,architect,architecture,arctic,area,argue,argument,arise,arithmetic,arm,armchair,army,around"
 "arrest,arrival,arrive,arrow,art,article,artificial,artist,as,ash,ashamed,aside,ask,asleep,aspect,assess,assessment,assign,assist,assistance,"
 "assistant,associate,association,assume,assumption,astonish,astronaut,astronomer,astronomy,at,athlete,athletic,atmosphere,atom,attach,attack,attain"
 "attitude,attract,attraction,attractive,audience,aunt,authentic,author,authority,automatic,autonomous,autumn,available,avenue,average,avoid,awake"
 "awesome,awful,awkward,"
 "baby,bachelor,back,background,backward,bacon,bad,badly,bag,baggage,bake,bakery,balance,balcony,ball,ballet,balloon,bamboo,ban,banana,"
 "band,bandage,bank,bar,barbecue,barber,bare,bargain,bark,barrier,base,baseball,basement,basic,basin,basis,basket,basketball,bat,bath,"
 "bathe,bathroom,battery,battle,bay,be,beach,bean,bear,beard,beast,beat,beautiful,beauty,because,become,bed,bedroom,bee,beef,"
 "beer,before,beg,begin,beginning,behalf,behave,behavior,behind,being,belief,believe,bell,belong,below,belt,bench,bend,beneath,benefit,"
 "beside,besides,best,bet,betray,better,between,beyond,bicycle,bid,big,bike,bill,billion,bind,biology,bird,birth,birthday,biscuit,"
 "bit,bite,bitter,black,blackboard,blame,blank,blanket,bleed,bless,blind,block,blood,blouse,blow,blue,board,boast,boat,body,"
 "boil,bomb,bond,bone,bonus,book,boom,boot,border,bore,born,borrow,boss,both,bother,bottle,bottom,bounce,bound,boundary,"
 "bow,bowl,box,boy,brain,brake,branch,brand,brave,bread,break,breakfast,breast,breath,breathe,breed,brick,bridge,brief,bright,"
 "brilliant,bring,broad,broadcast,broken,broom,brother,brown,brush,budget,build,building,bunch,burden,burn,burst,bury,bus,bush,business,"
 "busy,but,butcher,butter,button,buy,by,bye,"
 "cabbage,cafe,cage,cake,calculate,call,calm,camera,camp,can,canal,cancel,cancer,candidate,candle,candy,cap,capital,captain,car,"
 "carbon,card,care,career,careful,careless,carpet,carrot,carry,cart,case,cash,cast,castle,cat,catch,category,cattle,cause,cave,"
 "ceiling,celebrate,cell,cent,center,century,ceremony,certain,certificate,chain,chair,chairman,chalk,challenge,champion,chance,change,channel,chapter"
 "charge,charity,chart,chase,chat,cheap,cheat,check,cheek,cheer,cheese,chef,chemical,chemist,chemistry,chest,chew,chicken,chief,child,"
 "childhood,chocolate,choice,choose,church,cigarette,cinema,circle,citizen,city,civil,claim,clap,class,classic,classroom,clean,clear,clerk,clever,"
 "climate,climb,clinic,clock,clone,close,cloth,clothes,cloud,club,coach,coal,coast,coat,code,coffee,coin,cold,collar,colleague,"
 "collect,college,colour,column,comb,combine,come,comfort,command,comment,commit,common,communicate,company,compare,compete,complain,complete,computer"
 "concept,concern,concert,conclusion,condition,conduct,conference,confidence,confirm,conflict,confuse,congratulate,connect,conscious,consequence"
 "consume,contact,contain,contemporary,content,contest,context,continent,continue,contract,contrary,contribute,control,convenient,conversation"
 "corner,correct,cost,cotton,cough,count,country,couple,courage,course,court,cousin,cover,cow,crash,create,credit,crime,crisis,criticism,"
 "crop,cross,crowd,cruel,cry,culture,cup,cure,curious,current,curtain,customer,cut,cycle,"
 "dad,daily,damage,damp,dance,danger,dangerous,dare,dark,darkness,dash,data,database,date,daughter,dawn,day,dead,deadline,deal,"
 "dear,death,debate,debt,decade,decide,decision,declare,decline,decorate,decrease,deep,deer,defeat,defence,defend,degree,delay,delete,deliberate,"
 "delicate,deliver,demand,dentist,deny,depart,department,depend,deposit,depth,describe,description,desert,deserve,design,desire,desk,desperate"
 "destroy,detail,detect,determine,develop,devote,dialog,diamond,diary,dictation,dictionary,die,diet,differ,difference,difficult,difficulty,dig"
 "dignity,dilemma,dimension,dinner,dip,direct,direction,director,directory,dirt,disable,disappear,disappoint,disaster,discount,discover,discovery"
 "dish,disk,dismiss,display,distance,distant,distribute,district,disturb,dive,divide,divorce,do,doctor,document,dog,dollar,domestic,dominate,donate"
 "double,doubt,down,download,downtown,dozen,draft,drag,dragon,drama,draw,dream,dress,drill,drink,drive,drop,drought,drug,drum,"
 "dry,duck,due,dull,dumpling,during,dust,duty,dynamic,"
 "each,eager,eagle,ear,early,earn,earth,earthquake,ease,east,eastern,easy,eat,ecology,edge,edition,editor,educate,education,effect,"
 "effort,egg,eight,either,elder,elect,electric,electricity,electronic,elephant,eleven,else,email,embarrass,embassy,emergency,emperor,employ,empty"
 "encourage,end,ending,endless,enemy,energy,engage,engine,engineer,enjoy,enough,enter,entertain,enthusiasm,entire,entrance,envelope,environment,envy"
 "equip,equipment,eraser,error,escape,especially,essay,establish,estate,estimate,evaluate,even,evening,event,eventually,ever,every,evidence,evil"
 "examine,example,excellent,except,exchange,excite,excuse,exercise,exhibition,exist,exit,expand,expect,expense,experiment,expert,explain,explode"
 "expose,express,expression,extra,extraordinary,extreme,eye,"
 "face,facial,facility,fact,factory,fail,failure,fair,faith,fall,false,familiar,family,famous,fan,fancy,fantastic,far,farm,farmer,"
 "fashion,fast,fasten,fat,father,fault,favor,favourite,fear,feast,feather,feature,federal,feed,feel,fellow,female,fence,ferry,festival,"
 "fetch,fever,few,fiction,field,fierce,fifteen,fifth,fifty,fight,figure,file,fill,film,final,finance,find,fine,finger,finish,"
 "fire,firm,first,fish,fist,fit,five,fix,flag,flame,flash,flat,flavor,flee,flesh,flexible,flight,float,flood,floor,"
 "flour,flow,flower,flu,fluent,fly,focus,fog,fold,folk,follow,fond,food,fool,foot,football,for,forbid,force,forecast,"
 "forehead,foreign,forest,forever,forget,forgive,fork,form,format,former,fortnight,fortunate,fortune,forty,forward,found,fountain,four,fourteen"
 "fragile,fragrant,framework,free,freeze,frequent,fresh,friday,fridge,friend,friendly,friendship,frighten,frog,from,front,fruit,fry,fuel,full,"
 "fun,function,fundamental,funny,furniture,further,future,"
 "gain,gallery,game,garage,garbage,garden,gas,gate,gather,gay,general,generation,generous,gentle,gentleman,geography,geometry,gesture,get,gift,"
 "gifted,girl,give,glad,glance,glass,global,globe,glory,glove,glue,go,goal,goat,god,gold,golden,good,goods,goose,"
 "government,grade,gradual,graduate,grammar,grand,grandchild,granddaughter,grandfather,grandma,grandmother,grandpa,grandson,granny,grape,graph,grasp"
 "greedy,green,greengrocer,greet,grey,grill,grocery,ground,group,grow,growth,guarantee,guard,guess,guest,guide,guilty,guitar,gun,gym,"
 "habit,hair,half,hall,ham,hamburger,hammer,hand,handbag,handful,handle,handsome,handwriting,hang,happen,happily,happiness,happy,harbour,hard,"
 "hardly,hardworking,harm,harmful,harvest,hat,hate,have,he,head,headache,headline,health,healthy,hear,heart,heat,heaven,heavy,heel,"
 "height,helicopter,hello,help,helpful,hen,her,herb,here,hero,hers,herself,hi,hide,high,highway,hill,him,himself,hire,"
 "his,history,hit,hobby,hold,hole,holiday,home,homeland,hometown,homework,honest,honey,honour,hook,hope,hopeful,hopeless,horrible,horse,"
 "hospital,host,hostess,hot,hotel,hour,house,housewife,housework,how,however,hug,huge,human,humorous,hundred,hunger,hungry,hunt,hurry,hurt,"
 "husband,"
 "I,ice,idea,ideal,identity,idiom,if,ignore,ill,illegal,illness,imagine,immediate,immigrate,impact,import,importance,important,impossible,impress,"
 "impression,improve,in,inch,incident,include,income,increase,indeed,independent,indicate,industry,influence,inform,information,initial,injure,injury"
 "insect,insert,inside,insist,inspect,inspire,instance,instant,instead,instrument,insurance,insure,intelligence,intend,intention,interest"
 "interval,interview,into,introduce,introduction,invent,invitation,invite,iron,island,isolate,issue,it,its,itself,"
 "jacket,jam,jar,jaw,jazz,jeans,jet,jet,jewelry,job,jog,join,joke,journal,journey,joy,judge,juice,jump,junior,"
 "just,justice,"
 "kangaroo,keen,keep,kettle,key,keyboard,kick,kid,kill,kilo,kilogram,kilometre,kind,kindergarten,king,kingdom,kiss,kitchen,kite,knee,"
 "knife,knock,know,knowledge,"
 "lab,labor,labour,lack,ladder,lady,lake,lamb,lamp,land,language,lantern,lap,large,last,late,later,laugh,laughter,launch,"
 "law,lawyer,lay,lazy,lead,leader,leaf,league,leak,learn,least,leather,leave,lecture,left,leg,legal,lemon,lemonade,lend,"
 "length,less,lesson,let,letter,level,liberate,library,license,lid,lie,life,lift,light,lightning,like,likely,limit,line,link,"
 "lion,lip,list,listen,literature,litre,litter,little,live,lively,load,loaf,local,lock,lonely,long,look,loose,lord,lorry,"
 "lose,loss,lot,loud,love,lovely,low,luck,lucky,luggage,lunch,lung,"
 "machine,mad,madam,magazine,magic,magnificent,mail,main,mainland,major,majority,make,male,man,manage,manager,mankind,manor,many,map,"
 "marathon,marble,march,mark,market,marriage,marry,mask,mass,master,match,material,mathematics,matter,maximum,may,maybe,me,meal,mean,"
 "meaning,means,meanwhile,measure,meat,mechanic,medal,media,medical,medicine,medium,meet,meeting,member,memory,mend,mental,mention,menu,merchant,"
 "mercy,mere,merry,message,messy,metal,method,metre,microphone,microwave,middle,midnight,might,mild,mile,milk,million,mind,mine,mineral,"
 "minibus,minimum,minister,minority,minus,minute,miracle,mirror,miss,missile,mistake,mix,mixture,mobile,model,modem,modern,modest,moment,monitor,"
 "monkey,month,moon,moral,more,morning,mosquito,most,mother,motor,mountain,mouse,mouth,move,movement,movie,much,mud,murder,museum,"
 "mushroom,music,musical,must,my,myself,mystery,"
 "nail,name,narrow,nation,national,native,natural,nature,navy,near,nearby,nearly,neat,necessary,neck,need,needle,negative,negotiate,neighbour,"
 "neither,nephew,nervous,nest,net,network,never,new,news,newspaper,next,niece,night,no,noble,nobody,nod,noise,none,noodle,"
 "noon,nor,normal,north,northern,nose,not,note,notebook,nothing,notice,novel,now,nuclear,number,nurse,nut,"
 "obey,object,observe,obtain,obvious,occupation,occupy,occur,ocean,odd,of,off,offence,offend,offer,office,officer,official,often,oil,"
 "ok,old,on,once,one,oneself,onion,online,only,onto,open,operate,operation,operator,opinion,oppose,opposite,optimistic,option,or,"
 "oral,orange,orbit,order,ordinary,organ,organization,organize,origin,other,otherwise,ought,our,ours,ourselves,out,outcome,outdoor,outer,outgoing,"
 "outing,outline,output,outside,outstanding,over,overcome,overlook,overseas,owe,own,owner,"
 "pace,pacific,pack,package,page,paid,pain,paint,pair,palace,pale,pan,panda,panic,paper,paragraph,parallel,parcel,pardon,parent,"
 "park,part,particular,partly,partner,party,pass,passage,passenger,passion,passive,passport,past,patience,patient,pattern,pause,pay,payment,peace,"
 "peaceful,peach,peak,pear,pedestrian,pen,pencil,penny,people,pepper,per,percent,perfect,perform,performance,perfume,perhaps,period,permanent,per,it"
 "person,personal,personality,persuade,pet,petrol,phone,photo,photograph,phrase,physical,physician,physics,piano,pick,picnic,picture,pie,piece,pig,"
 "pile,pill,pillow,pilot,pin,pink,pioneer,pipe,pity,place,plain,plan,plane,planet,plant,plastic,plate,platform,play,player,"
 "pleasant,please,pleasure,plenty,plot,plug,plus,pocket,poem,poet,poetry,point,poison,pole,police,policy,polite,political,pollute,pollution,"
 "pool,poor,pop,popular,population,pork,port,position,positive,possess,possession,possible,post,poster,postman,pot,potato,potential,pound,pour,"
 "powder,power,practical,practice,praise,pray,precious,prefer,prepare,presentation,president,press,pressure,pretend,pretty,prevent,preview,previous"
 "primary,print,prison,private,prize,probably,problem,procedure,proceed,process,produce,product,profession,professor,profit,programme,progress,project"
 "proper,protect,protection,proud,prove,provide,province,psychology,pub,public,publish,pull,punctual,punish,pupil,purchase,pure,purple,purpose,purse"
 "push,put,puzzle,"
 "qualification,quality,quantity,quarrel,quarter,queen,question,quick,quiet,quit,quite,quiz,"
 "rabbit,race,racial,radio,rail,rain,raise,random,range,rank,rapid,rare,rat,rate,rather,raw,ray,reach,react,read,"
 "ready,real,realize,really,reason,reasonable,receive,recent,record,recover,recycle,red,reduce,refer,reflect,reform,refuse,regard,register,regret,"
 "regular,reject,relate,relation,relative,relax,release,relevant,reliable,relief,religion,rely,remain,remark,remember,remind,remote,remove,rent"
 "repeat,replace,reply,report,represent,republic,request,require,rescue,research,reserve,resign,resist,resolve,resource,respond,responsibility,rest"
 "result,retire,return,review,revolution,reward,rice,rich,ride,right,ring,rise,risk,river,road,robot,rock,role,roll,roof,"
 "room,root,rope,rose,rough,round,route,row,rubber,rubbish,rude,ruin,rule,ruler,run,rural,rush,"
 "sacred,sad,safe,safety,sail,salad,salary,sale,salt,same,sand,sandwich,satellite,satisfaction,satisfy,saturday,save,saucer,sausage,say,"
 "scale,scan,scar,scare,scarf,scene,scenery,scholar,school,science,scientist,scissors,score,scratch,scream,screen,sea,search,season,seat,"
 "second,secret,section,secure,see,seed,seek,seem,seize,seldom,select,self,sell,send,senior,sense,sentence,separate,series,serious,"
 "servant,serve,service,set,settle,seven,seventeen,seventh,seventy,several,severe,sew,sex,shade,shadow,shake,shall,shallow,shame,shape,"
 "share,shark,sharp,shave,she,sheep,sheet,shelf,shelter,shine,ship,shirt,shock,shoe,shoot,shop,shore,short,shortly,shot,"
 "should,shoulder,shout,show,shower,shut,shy,sick,side,sight,sign,signal,significance,silence,silent,silk,silly,silver,similar,simple,"
 "simply,since,sing,single,sink,sir,sister,sit,situation,six,sixteen,sixth,sixty,size,skate,ski,skill,skin,skip,skirt,"
 "sky,slave,sleep,sleeve,slice,slide,slight,slip,slow,small,smart,smell,smile,smog,smoke,smooth,snake,snow,so,soap,"
 "soccer,social,society,sock,soda,soft,soil,solar,soldier,solid,solve,some,somebody,someone,something,sometimes,somewhat,somewhere,son,song,"
 "soon,sorry,sort,soul,sound,soup,sour,south,southern,space,spare,speak,speaker,special,specific,speech,speed,spell,spend,spin,"
 "spirit,spoon,sport,spot,spread,spring,square,stable,stadium,staff,stage,stair,stamp,stand,standard,star,stare,start,state,station,"
 "status,stay,steady,steal,steam,steel,steep,step,stick,still,stock,stomach,stone,stop,storage,store,storm,story,straight,strange,"
 "strategy,straw,stream,street,strength,stress,strict,strike,string,strong,struggle,student,studio,study,stupid,style,subject,submit,subscribe"
 "succeed,success,such,sudden,suffer,sugar,suggest,suit,suitable,suitcase,summary,summer,sun,super,supermarket,supply,support,suppose,sure,surface,"
 "surprise,surround,survey,survive,suspect,suspend,sustain,swallow,swap,swear,sweat,sweater,sweep,sweet,swim,swing,switch,symbol,sympathy,system,"
 # T-Z 完整列表
 "table,tablet,tail,tailor,take,tale,talent,talk,tall,tank,tap,tape,target,task,taste,taxi,tea,teach,teacher,team,"
 "tear,technical,technique,technology,teenager,telephone,television,tell,temperature,temple,ten,tend,tennis,tense,tent,term,terrible,test,text,than"
 "thank,that,the,theatre,theft,their,theirs,them,theme,themselves,then,theory,there,therefore,these,they,thick,thief,thin,thing,"
 "think,third,thirsty,thirteen,thirty,this,thorough,those,though,thought,thousand,thread,threat,three,thrill,throat,through,throughout,throw,thunder"
 "thursday,thus,ticket,tide,tidy,tie,tiger,tight,till,time,tiny,tip,tire,tired,title,to,toast,tobacco,today,together,"
 "toilet,tomato,tomorrow,ton,tone,tongue,tonight,too,tool,tooth,top,topic,total,touch,tough,tour,tourist,toward,towel,tower,"
 "town,toy,track,trade,tradition,traffic,train,training,translate,transport,trap,travel,treasure,treat,treatment,tree,tremble,trend,trial,trick,"
 "trip,trouble,truck,true,trust,truth,try,tube,tuesday,tune,turn,tutor,twelfth,twelve,twentieth,twenty,twice,twin,twist,two,type,"
 "ugly,umbrella,unable,uncle,under,underground,understand,undo,unemployment,unfair,unfortunately,uniform,union,unique,unit,unite,university,unknown"
 "until,unusual,up,update,upon,upper,upset,urban,urge,us,use,used,useful,usual,usually,"
 "vacation,valley,valuable,value,vanilla,van,variety,various,vase,vast,vegetable,vehicle,version,vertical,very,victory,video,view,village,vinegar,"
 "violence,violent,violin,virtual,virtue,virus,visa,visit,visitor,visual,vital,vivid,vocabulary,voice,volcano,volleyball,volume,voluntary,volunteer"
 "wage,waist,wait,waiter,wake,walk,wall,wallet,wander,want,war,ward,warehouse,warm,warn,warning,wash,waste,watch,water,"
 "watermelon,wave,way,we,weak,wealth,weapon,wear,weather,web,website,wedding,week,weekend,weep,weigh,weight,welcome,welfare,well,"
 "west,western,wet,whale,what,whatever,wheat,wheel,when,whenever,where,wherever,whether,which,whichever,while,whisper,white,who,whole,"
 "whom,whose,why,wide,widespread,wife,wild,will,willing,win,wind,window,windy,wine,wing,wink,winner,winter,wire,wisdom,"
 "wise,wish,with,withdraw,within,without,witness,woman,wonder,wonderful,wood,wool,word,work,world,worldwide,worried,worry,worth,worthy,"
 "would,wound,wrap,wrist,write,wrong,"
 "yard,yeah,year,yell,yellow,yes,yesterday,yet,yoghurt,you,young,your,yours,yourself,youth,"
 "zebra,zero,zone,zoo")

ALL_WORDS = [w.strip() for w in WORD_STR.split(",") if w.strip()]

def load_api_key():
    config_path = os.path.join(DATA_DIR, "ai_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("api_key_free", "").strip()
    return ""

def generate_one(word):
    prompt = f"""请为英语单词"{word}"生成完整学习数据，严格按以下JSON格式输出（不要包含任何其他内容）：
{{
  "phonetic": "英式音标",
  "meaning": "详细中文释义，包含不同词性的含义",
  "example": "一个高中难度的例句",
  "forms": "变形和派生形式（如复数、过去式、比较级等，用逗号分隔，例如：abandons, abandoning, abandoned）",
  "grammar": {{
    "patterns": ["句型结构"],
    "collocations": ["固定搭配"],
    "notes": ["语法要点"],
    "discrimination": ["近义词辨析"],
    "test_points": ["常考考点"]
  }}
}}
只输出这个JSON对象。"""
    api_key = load_api_key()
    if not api_key: return None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }
    for retry in range(3):
        try:
            resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                 headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                # 确保字段完整
                data.setdefault("meaning", "")
                data.setdefault("phonetic", "")
                data.setdefault("example", "")
                data.setdefault("forms", "")
                if "grammar" not in data:
                    data["grammar"] = {"patterns": [], "collocations": [], "notes": [], "discrimination": [], "test_points": []}
                else:
                    for field in ["patterns", "collocations", "notes", "discrimination", "test_points"]:
                        data["grammar"].setdefault(field, [])
                return data
        except:
            time.sleep(2)
    return None

def main():
    api_key = load_api_key()
    if not api_key:
        print("❌ 未配置 API 密钥")
        return

    existing_words = set()
    if os.path.exists(VOCAB_FILE):
        with open(VOCAB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    w = json.loads(line).get("word")
                    if w: existing_words.add(w.lower())
                except: pass

    remaining = [w for w in ALL_WORDS if w.lower() not in existing_words]
    print(f"📊 总词汇: {len(ALL_WORDS)}，已完成: {len(existing_words)}，剩余: {len(remaining)}")

    for idx, word in enumerate(remaining, 1):
        print(f"⏳ [{idx}/{len(remaining)}] 正在生成 {word} ...", end=" ")
        word_data = None
        for _ in range(3):
            word_data = generate_one(word)
            if word_data: break
            time.sleep(2)
        if word_data:
            entry = {
                "word": word,
                "phonetic": word_data.get("phonetic", ""),
                "meaning": word_data.get("meaning", ""),
                "example": word_data.get("example", ""),
                "forms": word_data.get("forms", ""),
                "grammar": word_data.get("grammar", {})
            }
            with open(VOCAB_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print("✅")
        else:
            print("❌ 失败")

    print("🎉 全部完成！")

if __name__ == "__main__":
    main()